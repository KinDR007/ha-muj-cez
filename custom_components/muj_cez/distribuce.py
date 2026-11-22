"""ČEZ Distribuce portal (dip.cezdistribuce.cz): HDO switching times.

The distribution portal uses the same ČEZ ID credentials as muj.cez.cz but a different
sign-in (CAS on mepas.cez.cz). Login flow, endpoints and the landing environment
selection follow https://github.com/MattXcz/CEZ (MIT, Matouš Bečvář).

`casy` of a signal are the low tariff (NT) intervals of the day, local time, e.g.
"00:00-10:00;   11:00-12:00;   18:00-24:00".
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import aiohttp

from .grid import TZ

_LOGGER = logging.getLogger(__name__)

CAS_URL = "https://mepas.cez.cz/cas"
CLIENT_ID = "emiCuDBbivwYxraX.dip.dip.ext.zak.prod.v1"
BASE_URL = "https://dip.cezdistribuce.cz/irj/portal"
TIMEOUT = aiohttp.ClientTimeout(total=30)
# The portal sends very long headers; aiohttp's defaults reject them.
MAX_HEADER = 8190 * 4
# Environment chosen when the account has several (household first).
ENVIRONMENT_PRIORITY = ("D", "P", "S", "O", "PND")
LANDING_STEPS = 3

LOW = "low"
HIGH = "high"

_EXECUTION = re.compile(r'name="execution"\s+value="([^"]+)"|value="([^"]+)"\s+name="execution"')


class DipError(Exception):
    """Distribution portal unavailable or unexpected response."""


class DipAuthError(DipError):
    """Credentials rejected or a manual step is needed in the portal."""


def new_session(**kwargs: Any) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(**kwargs)


class DipClient:
    """Short lived client: `async with DipClient(user, password) as c: await c.signals(ean)`.

    `session_factory(**kwargs)` creates the session with its own cookie jar; on exit it
    is closed, or detached (`detach=True`) when it shares the connector of Home
    Assistant (async_create_clientsession), whose close must not be called.
    """

    def __init__(
        self,
        username: str,
        password: str,
        session_factory: Callable[..., aiohttp.ClientSession] = new_session,
        detach: bool = False,
    ) -> None:
        self._username = username
        self._password = password
        self._factory = session_factory
        self._detach = detach
        self._session: aiohttp.ClientSession | None = None
        self._token: str | None = None

    async def __aenter__(self) -> DipClient:
        self._session = self._factory(
            cookie_jar=aiohttp.CookieJar(),
            timeout=TIMEOUT,
            max_line_size=MAX_HEADER,
            max_field_size=MAX_HEADER,
        )
        try:
            await self._login()
        except BaseException:
            await self._release()
            raise
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._release()

    async def _release(self) -> None:
        session, self._session = self._session, None
        if session is None:
            return
        if self._detach:
            session.detach()
        else:
            await session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        assert self._session is not None
        return self._session

    async def _login(self) -> None:
        redirect = f"{BASE_URL}/common-api?path=/common/header"
        authorize = (
            f"{CAS_URL}/oidc/oidcAuthorize?response_type=code"
            f"&redirect_uri={urllib.parse.quote(redirect, safe='')}"
            f"&client_id={CLIENT_ID}&scope=openid"
        )
        try:
            async with self.session.get(authorize) as resp:
                login_url = str(resp.url)
                html = await resp.text()
            if "/cas/login" not in login_url:
                raise DipError(f"unexpected authorize redirect to {resp.url.host}")
            match = _EXECUTION.search(html)
            if not match:
                raise DipError("login form without execution token")
            form = {
                "username": self._username,
                "password": self._password,
                "execution": match.group(1) or match.group(2),
                "_eventId": "submit",
                "geolocation": "",
            }
            async with self.session.post(login_url, data=form) as resp:
                portal = resp.url.host == urllib.parse.urlparse(BASE_URL).hostname
                # The portal landing iView answers 404 to non browser clients; the
                # session is established anyway once the code reached the portal.
                if not portal:
                    raise DipAuthError("login rejected or a manual step is needed")
            self._token = await self._fetch_token()
            await self._landing()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DipError(f"login failed: {err}") from err

    async def _fetch_token(self) -> str:
        async with self.session.get(f"{BASE_URL}/rest-auth-api?path=/token/get") as resp:
            data = await _json(resp)
        token = (
            data if isinstance(data, str) else (data or {}).get("data") or (data or {}).get("token")
        )
        if not isinstance(token, str) or not token:
            raise DipAuthError("portal returned no API token")
        return token

    async def _request(self, method: str, path: str, body: Any = None) -> Any:
        headers = {"X-Request-Token": self._token or ""}
        async with self.session.request(
            method, f"{BASE_URL}/{path}", headers=headers, json=body
        ) as resp:
            if method == "POST" and resp.status < 400 and not (await resp.text()).strip():
                return None
            raw = await _json(resp)
        if isinstance(raw, dict) and "statusCode" in raw:
            if raw["statusCode"] != 200:
                raise DipError(f"{path.split('?')[0]}: statusCode {raw['statusCode']}")
            return raw.get("data")
        return raw

    async def _landing(self) -> None:
        """Select the portal environment when the account has several (else no-op)."""
        for _ in range(LANDING_STEPS):
            try:
                check = await self._request("GET", "landing?path=check")
            except DipError as err:
                _LOGGER.debug("Landing check failed, continuing: %s", err)
                return
            if not isinstance(check, dict) or check.get("anyCheckNeeded") is False:
                return
            if check.get("accessConditions") or check.get("spopContract"):
                raise DipAuthError("terms of use must be confirmed in dip.cezdistribuce.cz")
            if not check.get("environmentSelect"):
                return
            data = await self._request("GET", "landing?path=select-environment")
            env_id, partner_id = choose_environment(data)
            await self._request(
                "POST",
                f"landing?path=select-environment/{urllib.parse.quote(env_id)}"
                f"/{urllib.parse.quote(partner_id)}",
            )
        raise DipError("environment selection did not complete")

    async def signals(self, ean: str) -> Any:
        """Raw HDO signals of a supply point (None when it has no HDO)."""
        try:
            return await self._request("GET", f"prehled-om?path=supply-point-detail/signals/{ean}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DipError(f"signals: {err}") from err


async def _json(resp: aiohttp.ClientResponse) -> Any:
    text = await resp.text()
    if resp.status >= 400:
        raise DipError(f"HTTP {resp.status} from {resp.url.path}")
    try:
        return json.loads(text) if text.strip() else None
    except ValueError as err:
        raise DipError(f"no JSON from {resp.url.path} (HTTP {resp.status})") from err


def choose_environment(data: Any) -> tuple[str, str]:
    """Environment and partner to select: the portal's preselection, by priority."""
    options: list[tuple[int, int, str, str]] = []
    envs = data.get("environments") if isinstance(data, dict) else None
    for env in envs or []:
        env_id = env.get("environmentId")
        if not env_id:
            continue
        rank = (
            ENVIRONMENT_PRIORITY.index(env_id)
            if env_id in ENVIRONMENT_PRIORITY
            else len(ENVIRONMENT_PRIORITY)
        )
        for partner in env.get("partners") or []:
            pid = partner.get("partnerId")
            if pid:
                preselected = 0 if str(env.get("selectedPartnerId")) == str(pid) else 1
                options.append((rank, preselected, env_id, str(pid)))
    if not options:
        raise DipError("environment selection offered no partner")
    _, _, env_id, pid = min(options)
    return env_id, pid


# ---------------------------------------------------------------------------
# HDO schedule (pure functions)
# ---------------------------------------------------------------------------


def _minutes(value: str) -> int | None:
    try:
        hours, minutes = value.strip().split(":")
        total = int(hours) * 60 + int(minutes)
    except ValueError:
        return None
    return total if 0 <= total <= 24 * 60 else None


def parse_signals(data: Any) -> dict[str, Any] | None:
    """{"signal", "signals", "days": {iso date: [["HH:MM", "HH:MM"], ...]}} or None.

    With several signals (e.g. a separate one for a water heater) the first one is the
    tariff signal; the others are listed in "signals".
    """
    rows = data.get("signals") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        return None
    names = list(dict.fromkeys(str(r.get("signal") or "") for r in rows if r.get("signal")))
    if not names:
        return None
    days: dict[str, list[list[str]]] = {}
    for row in rows:
        if row.get("signal") != names[0]:
            continue
        try:
            day = datetime.strptime(str(row.get("datum")), "%d.%m.%Y").date()
        except ValueError:
            continue
        intervals = []
        for part in str(row.get("casy") or "").split(";"):
            start, sep, end = part.strip().partition("-")
            if sep and _minutes(start) is not None and _minutes(end) is not None:
                intervals.append([start.strip(), end.strip()])
        days[day.isoformat()] = intervals
    if not days:
        return None
    return {"signal": names[0], "signals": names, "days": dict(sorted(days.items()))}


def _at(day: date, value: str) -> datetime:
    """Local wall clock time of the day ("24:00" = next midnight) as UTC.

    UTC keeps comparisons and durations right on DST change days.
    """
    minutes = _minutes(value) or 0
    local = datetime(day.year, day.month, day.day, tzinfo=TZ) + timedelta(minutes=minutes)
    return local.astimezone(UTC)


def low_windows(schedule: dict[str, Any]) -> list[tuple[datetime, datetime]]:
    """Merged NT windows (adjacent intervals, also across midnight, joined)."""
    windows: list[tuple[datetime, datetime]] = []
    for iso, intervals in sorted((schedule.get("days") or {}).items()):
        day = date.fromisoformat(iso)
        for start, end in intervals:
            begin = _at(day, start)
            finish = _at(day, end)
            if finish <= begin:
                continue
            if windows and windows[-1][1] >= begin:
                windows[-1] = (windows[-1][0], max(windows[-1][1], finish))
            else:
                windows.append((begin, finish))
    return windows


def schedule_end(schedule: dict[str, Any]) -> datetime | None:
    days = sorted(schedule.get("days") or {})
    return _at(date.fromisoformat(days[-1]), "24:00") if days else None


def hdo_state(schedule: dict[str, Any] | None, now: datetime) -> dict[str, Any] | None:
    """Tariff at `now` and the next switch; None outside the known schedule."""
    if not schedule or not schedule.get("days"):
        return None
    first = _at(date.fromisoformat(min(schedule["days"])), "00:00")
    end = schedule_end(schedule)
    if end is None or not first <= now < end:
        return None
    windows = low_windows(schedule)
    current = next((w for w in windows if w[0] <= now < w[1]), None)
    if current:
        tariff, switch = LOW, current[1]
    else:
        tariff = HIGH
        switch = next((w[0] for w in windows if w[0] > now), None)
    if switch is not None and switch >= end:
        switch = None  # the schedule ends there, the next switch is unknown
    local = now.astimezone(TZ).date()
    days = schedule["days"]
    return {
        "tariff": tariff,
        "next_switch": switch.astimezone(TZ) if switch else None,
        "signal": schedule.get("signal"),
        "signals": schedule.get("signals"),
        "today": [f"{a}-{b}" for a, b in days.get(local.isoformat(), [])],
        "tomorrow": [f"{a}-{b}" for a, b in days.get((local + timedelta(days=1)).isoformat(), [])],
        "low_hours_today": round(
            sum(
                (min(w[1], _at(local, "24:00")) - max(w[0], _at(local, "00:00"))).total_seconds()
                for w in windows
                if w[1] > _at(local, "00:00") and w[0] < _at(local, "24:00")
            )
            / 3600,
            2,
        ),
        "schedule_until": max(days),
    }


def prune(schedule: dict[str, Any], today: date) -> dict[str, Any]:
    """Drop days before yesterday (the stored schedule only grows otherwise)."""
    keep = (today - timedelta(days=1)).isoformat()
    days = {d: v for d, v in (schedule.get("days") or {}).items() if d >= keep}
    return {**schedule, "days": days}


def merge(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """New days win; older known days are kept (a failed day in between stays)."""
    days = dict((old or {}).get("days") or {})
    days.update(new.get("days") or {})
    return {**new, "days": dict(sorted(days.items()))}
