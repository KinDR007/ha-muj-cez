"""Live check of the ČEZ Distribuce HDO client.

CEZ_USER=... CEZ_PASS=... .venv/bin/python tools/hdo_smoke.py <EAN> [<EAN> ...]
Prints the parsed schedule and the tariff now; never prints credentials.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.util import dt as dt_util  # noqa: E402

from custom_components.muj_cez import distribuce  # noqa: E402


async def main(eans: list[str]) -> int:
    user, pwd = os.environ.get("CEZ_USER"), os.environ.get("CEZ_PASS")
    if not user or not pwd or not eans:
        print(__doc__)
        return 2
    try:
        async with distribuce.DipClient(user, pwd) as dip:
            print("login OK")
            for ean in eans:
                schedule = distribuce.parse_signals(await dip.signals(ean))
                if schedule is None:
                    print(f"...{ean[-4:]}: no HDO")
                    continue
                state = distribuce.hdo_state(schedule, dt_util.now(distribuce.TZ))
                print(f"...{ean[-4:]}: signals {schedule['signals']}, days {len(schedule['days'])}")
                print(
                    f"  now {state and state['tariff']}, next switch {state and state['next_switch']}"
                )
                print(f"  today {state and state['today']}")
    except distribuce.DipError as err:
        print(f"FAILED: {type(err).__name__}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"))
    sys.exit(asyncio.run(main(sys.argv[1:])))
