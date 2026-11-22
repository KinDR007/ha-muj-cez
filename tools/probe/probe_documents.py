"""One-off capture of invoice data files (CSV zip, PDF) and the product calculator.

Usage: CEZ_USER=... CEZ_PASS=... CEZ_SNAPSHOT_DIR=.snapshot/<name> \
  .venv/bin/python tools/probe/probe_documents.py [invoices per contract, default 2]

Invoices are picked from a fresh /billings/extended (document header/snapshot ids change).
Output goes to <CEZ_SNAPSHOT_DIR>/docs/ (git-ignored, personal data). Endpoints and
payloads follow the portal frontend (documents API, product-calculator API).
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import SNAPSHOT_DIR, api  # noqa: E402

OUT = SNAPSHOT_DIR / "docs"
RTT_SOURCE, OTHER_SOURCE = "SAP_R3_RT130", "SAP_R3_RQ140"


class Probe(api.CezClient):
    async def req(
        self, method: str, path: str, body: Any = None, binary: bool = False
    ) -> tuple[int, Any]:
        await self._ensure_token()
        headers = {
            "User-Agent": api.USER_AGENT,
            "Accept": "*/*" if binary else "application/json",
            "Authorization": f"Bearer {self._access_token}",
            **({api.PARTNER_HEADER: self.partner} if self.partner else {}),
        }
        async with self._session.request(
            method, f"{self._api_url}{path}", json=body, headers=headers, timeout=api.TIMEOUT
        ) as resp:
            data = await resp.read()
            if binary and resp.status == 200:
                return resp.status, (resp.headers.get("Content-Type", ""), data)
            try:
                return resp.status, json.loads(data) if data else None
            except ValueError:
                return resp.status, data[:500].decode(errors="replace")


def doc_params(row: dict) -> list[dict]:
    return [
        {"key": "PARTNER_ID_CRM", "value": row.get("partnerIdCrm")},
        {"key": "HEADER_ID", "value": str(row.get("billingAccountingDocumentHeaderId"))},
        {
            "key": "ACCOUNT_DOCUMENT_NUMBER",
            "value": row.get("billingReceivablesAndPayablesAccountDocumentNumber"),
        },
        {"key": "SNAPSHOT_ID", "value": row.get("billingBalanceSnapshotId")},
        {"key": "CONTRACT_ID_ISU", "value": row.get("agreementIdIsu")},
        {
            "key": "SOURCE_SYSTEM",
            "value": RTT_SOURCE if row.get("billingSourceSystem") == "RTT" else OTHER_SOURCE,
        },
    ]


def save(name: str, data: Any) -> None:
    path = OUT / name
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"  -> {path.relative_to(SNAPSHOT_DIR.parent.parent)}")


async def fetch_attachment(p: Probe, key: str, stem: str) -> None:
    status, res = await p.req("GET", f"/documents/{key}/attachment", binary=True)
    if status != 200:
        print(f"  attachment {stem}: HTTP {status} {res}")
        return
    ctype, data = res
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                print(f"  zip member {info.filename} ({info.file_size} B)")
                save(f"{stem}__{Path(info.filename).name}", zf.read(info))
    else:
        ext = "pdf" if data[:4] == b"%PDF" else "bin"
        print(f"  {ctype} {len(data)} B")
        save(f"{stem}.{ext}", data)


async def download_doc(p: Probe, guid: str, stem: str) -> None:
    status, res = await p.req("POST", f"/documents/{guid}/attachment")
    key = res.get("attachmentKey") if isinstance(res, dict) else None
    print(f"  prepare {stem}: HTTP {status} {str(res)[:150]}")
    if status == 200 and key:
        await fetch_attachment(p, key, stem)


async def probe_invoice(p: Probe, row: dict) -> None:
    number = row["billingReceivablesAndPayablesAccountDocumentNumber"]
    print(f"invoice {number} ({row.get('billingAccountingDocumentDate')})")
    filt = {"documentDomain": "INVOICES", "documentParams": doc_params(row)}
    # "Datový soubor.csv" in billing detail
    status, res = await p.req("POST", "/documents/attachment?withRetry=false&force=false", filt)
    print(f"  csv prepare: HTTP {status} {str(res)[:200]}")
    if status == 200 and isinstance(res, dict) and res.get("attachmentKey"):
        await fetch_attachment(p, res["attachmentKey"], f"{number}_csv")
    # invoice PDF
    status, docs = await p.req("POST", "/documents", filt)
    print(f"  documents: HTTP {status} {len(docs) if isinstance(docs, list) else docs}")
    if status == 200 and isinstance(docs, list):
        save(f"{number}_documents.json", docs)
        for i, doc in enumerate(docs[:2]):
            if doc.get("documentGuidCol"):
                await download_doc(p, doc["documentGuidCol"], f"{number}_pdf{i}")


async def probe_pricelists(p: Probe, place_id: str, ean: str) -> None:
    """Price list PDFs (DOC_TYPE CEN) of a supply point, as the billing detail lists them."""
    print(f"supply point documents {ean}")
    filt = {
        "documentDomain": "SUPPLY_POINT",
        "documentParams": [
            {"key": "SUPPLY_POINT_ID", "value": place_id},
            {"key": "CONSUMPTION_PLACE_ID", "value": ean},
        ],
    }
    status, docs = await p.req("POST", "/documents", filt)
    if status != 200 or not isinstance(docs, list):
        print(f"  documents: HTTP {status} {str(docs)[:200]}")
        return
    save(f"sp_documents_{ean}.json", docs)
    for i, doc in enumerate(docs):
        params = {x["key"]: x.get("value") for x in doc.get("documentParams", [])}
        if params.get("DOC_TYPE") == "CEN" and doc.get("documentGuidCol"):
            print(f"  {params.get('DOCUMENT_DESCRIPTION')} ({params.get('VALID_FROM')})")
            await download_doc(p, doc["documentGuidCol"], f"cenik_{ean}_{i}")


async def probe_calculator(p: Probe, agreement: str, ean: str, commodity: str = "E1") -> None:
    print(f"product calculator {agreement}/{ean}")
    status, products = await p.req(
        "GET", f"/product-calculator/{agreement}/products/{ean}?commodity={commodity}"
    )
    print(f"  products: HTTP {status} {str(products)[:300]}")
    save(f"calc_products_{agreement}.json", products)
    ids = []
    if isinstance(products, list):
        ids = [x.get("id") or x.get("productId") for x in products if isinstance(x, dict)]
    elif isinstance(products, dict):
        for v in products.values():
            if isinstance(v, list):
                ids += [x.get("id") or x.get("productId") for x in v if isinstance(x, dict)]
    ids = [i for i in ids if i][:5]
    body = {
        "commodity": commodity,
        "agreementIdIsu": agreement,
        "supplyPointCode": ean,
        "productCalculationInfo": [
            {"productId": i, "calculationDate": date.today().isoformat()} for i in ids
        ],
        "dateOfChange": date.today().isoformat(),
    }
    status, calc = await p.req("POST", "/product-calculator/calculations", body)
    print(f"  calculations: HTTP {status} {str(calc)[:300]}")
    save(
        f"calc_calculations_{agreement}.json", {"request": body, "status": status, "response": calc}
    )


async def main() -> int:
    user, pwd = os.environ.get("CEZ_USER"), os.environ.get("CEZ_PASS")
    if not user or not pwd:
        print("Set CEZ_USER and CEZ_PASS", file=sys.stderr)
        return 2
    per_contract = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text())["requests"]
    calc_files = [
        (k, v["file"])
        for k, v in manifest.items()
        if k.startswith("/product-calculator/") and v.get("file")
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        p = Probe(session, user, pwd)
        try:
            await p.authenticate()
            # Header and snapshot ids change over time: take them fresh, like the portal.
            since = date(date.today().year - 3, 1, 1).isoformat()
            status, billings = await p.req("GET", f"/billings/extended?dateFrom={since}")
            if status != 200 or not isinstance(billings, list):
                print(f"billings/extended: HTTP {status}", file=sys.stderr)
                return 1
            save("billings_extended.json", billings)
            picked: dict[str, list[dict]] = {}
            places: dict[str, str] = {}
            for row in sorted(
                billings, key=lambda r: r.get("billingAccountingDocumentDate") or "", reverse=True
            ):
                if row.get("billingAccountingDocumentType2") not in (
                    "INV",
                    "SLF",
                ):  # SLF = payout self-billing
                    continue
                if not row.get("billingReceivablesAndPayablesAccountDocumentNumber"):
                    continue
                lst = picked.setdefault(row["agreementIdIsu"], [])
                if len(lst) < per_contract:
                    lst.append(row)
                place = (row.get("consumptionPlaceInfo") or {}).get("consumptionPlaceIdIsu")
                if place:
                    places.setdefault(row["agreementIdIsu"], place)
            for rows in picked.values():
                for row in rows:
                    await probe_invoice(p, row)
            for key, f in calc_files:
                calc = json.loads((SNAPSHOT_DIR / f).read_text())
                agreement, ean = key.split("/")[2], key.split("/")[4].split("?")[0].strip()
                commodity = key.split("commodity=")[-1] if "commodity=" in key else "E1"
                # Consumption points only (gas has no tariff type).
                if calc.get("tariffType") or commodity.startswith("P"):
                    if agreement in places:
                        await probe_pricelists(p, places[agreement], ean)
                    await probe_calculator(p, agreement, ean, commodity)
        except api.CezError as err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
