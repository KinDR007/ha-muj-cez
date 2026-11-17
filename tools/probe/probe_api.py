"""GET API paths with saved token; save responses. Usage: probe_api.py path [path...]"""
import json, os, sys
import requests

OUT = os.path.join(os.path.dirname(__file__), "probe_out")
d = json.load(open(os.path.join(OUT, "token.json")))
rt = requests.post("https://api.cez.cz/token", data={
    "grant_type": "refresh_token", "refresh_token": d["tok"]["refresh_token"],
    "client_id": d["client_id"], "redirect_uri": "https://muj.cez.cz/col"})
if rt.ok:
    d["tok"] = rt.json()
    json.dump(d, open(os.path.join(OUT, "token.json"), "w"))
else:
    print("refresh failed", rt.status_code, rt.text[:200])
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Authorization": f"Bearer {d['tok']['access_token']}",
    "Accept": "application/json",
    **json.loads(os.environ.get("EXTRA_HEADERS", "{}")),
})
method = os.environ.get("METHOD", "GET")
body = os.environ.get("BODY")
for p in sys.argv[1:]:
    url = p if p.startswith("http") else d["api"] + p
    r = s.request(method, url, data=body, headers={"Content-Type": "application/json"} if body else None)
    name = p.strip("/").replace("/", "_").replace("?", "_")[:120] or "root"
    open(os.path.join(OUT, f"api_{name}.json"), "w").write(r.text)
    print(f"{r.status_code} {len(r.text):>7}B {p}  {r.text[:160]!r}")
