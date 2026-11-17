"""Probe: Muj CEZ login via plain HTTP (OAuth2 code + PKCE via WSO2 -> CAS)."""
import base64, hashlib, json, os, re, secrets, sys, uuid
from urllib.parse import urlparse, parse_qs, urljoin

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = "https://muj.cez.cz"
OUT = os.path.join(os.path.dirname(__file__), "probe_out")


def cfg(s):
    js = s.get(f"{BASE}/col/config.js").text
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', js))


def main():
    user, pwd = os.environ["CEZ_USER"], os.environ["CEZ_PASS"]
    os.makedirs(OUT, exist_ok=True)
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "cs-CZ,cs;q=0.9"})
    c = cfg(s)
    client_id = c["REACT_APP_CONSUMER_KEY"]
    redirect_uri = f"{BASE}/col"
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    scope = f"openid device_{uuid.uuid4()}"

    r = s.get(c["REACT_APP_AUTHORIZATION_ENDPOINT"], params={
        "client_id": client_id, "redirect_uri": redirect_uri, "scope": scope,
        "response_type": "code", "code_challenge": challenge,
        "code_challenge_method": "S256"})
    print("login page:", r.status_code, r.url[:80])
    m = re.search(r'name="execution"\s+value="([^"]+)"', r.text)
    if not m:
        sys.exit("no execution field")
    form_action = urljoin(r.url, re.search(r'id="fm1" action="([^"]+)"', r.text).group(1)
                          if re.search(r'id="fm1" action="([^"]+)"', r.text) else "login")
    # keep query string of login URL (service param)
    if "?" not in form_action:
        form_action += "?" + urlparse(r.url).query

    r = s.post(form_action, data={
        "username": user, "password": pwd, "execution": m.group(1),
        "_eventId": "submit", "geolocation": ""}, allow_redirects=False)
    code = None
    for _ in range(15):
        loc = r.headers.get("Location")
        print("  ->", r.status_code, (loc or r.url)[:110])
        if not loc:
            break
        if loc.startswith(redirect_uri):
            code = parse_qs(urlparse(loc).query).get("code", [None])[0]
            break
        r = s.get(urljoin(r.url, loc), allow_redirects=False)
    if not code:
        open(os.path.join(OUT, "fail.html"), "w").write(r.text)
        errs = re.findall(r'(?:error|alert)[^>]*>([^<]{5,200})', r.text)
        sys.exit(f"no code; page saved; hints: {errs[:3]}")

    t = s.post(c["REACT_APP_TOKEN_ENDPOINT"], data={
        "grant_type": "authorization_code", "code": code, "client_id": client_id,
        "redirect_uri": redirect_uri, "code_verifier": verifier, "scope": scope})
    print("token:", t.status_code)
    tok = t.json()
    print("token keys:", sorted(tok), "expires_in:", tok.get("expires_in"))
    json.dump({"tok": tok, "client_id": client_id, "scope": scope, "api": c["REACT_APP_API_URL"]},
              open(os.path.join(OUT, "token.json"), "w"))
    if "refresh_token" in tok:
        rt = s.post(c["REACT_APP_TOKEN_ENDPOINT"], data={
            "grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
            "client_id": client_id, "redirect_uri": redirect_uri})
        print("refresh:", rt.status_code)
        if rt.ok:
            json.dump({"tok": rt.json(), "client_id": client_id, "scope": scope,
                       "api": c["REACT_APP_API_URL"]}, open(os.path.join(OUT, "token.json"), "w"))


if __name__ == "__main__":
    main()
