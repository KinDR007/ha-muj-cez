"""Price breakdown from a snapshot (offline): invoices + current simulation per month.

Usage: [CEZ_SNAPSHOT_DIR=.snapshot/<name>] .venv/bin/python tools/prices_offline.py [--json]
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date

from offline import OfflineCezClient

sys.path.insert(0, str(__import__("offline").ROOT))
from custom_components.muj_cez import invoice, pricelist  # noqa: E402
from custom_components.muj_cez.pricing import pdf_fragments, pdf_text  # noqa: E402


async def main() -> int:
    client = OfflineCezClient()
    data = await client.fetch_all(client.captured_on or date.today())
    rows = await client.get_invoice_rows(date(2000, 1, 1))
    for spd in data.supply_points.values():
        sp = spd.supply_point
        if sp.production:
            continue
        agreements = {sp.agreement_id} | {
            s.supply_point.agreement_id
            for s in data.supply_points.values()
            if s.supply_point.production and s.supply_point.place_id == sp.place_id
        }
        invoices = []
        for row in rows:
            if row.get("agreementIdIsu") not in agreements:
                continue
            number = row["billingReceivablesAndPayablesAccountDocumentNumber"]
            text = await client.get_invoice_csv(row)
            parsed = invoice.parse_csv(number, text) if text else None
            if not parsed or not parsed.items:
                pdf = await client.get_invoice_pdf(row)
                if not pdf:
                    continue
                t = pdf_text(pdf)
                parsed = (
                    invoice.parse_payout_pdf_text(number, t)
                    if invoice.is_payout_text(t)
                    else invoice.parse_pdf_text(number, t)
                )
            invoices.append(parsed)
        lists = [
            parsed
            for path in sorted((client._dir / "docs").glob(f"cenik_{sp.ean}_*.pdf"))
            if (parsed := pricelist.parse(pdf_fragments(path.read_bytes())))
        ]
        c = spd.contract
        report = invoice.build_report(
            invoices,
            spd.sim_items,
            spd.simulation.measured_until if spd.simulation else None,
            invoice.weights_from_readings(spd.readings or []),
            pricelist.price_sources(
                lists,
                c.tariff_code if c else None,
                c.circuit_breaker if c else None,
                c.phase if c else None,
            ),
        )
        if "--json" in sys.argv:
            print(json.dumps(report, ensure_ascii=False, indent=1))
            continue
        print(f"== {sp.ean} ({len(invoices)} invoices)")
        for m in report["months"]:
            groups: dict[str, float] = {}
            for i in m["items"]:
                groups[i["group"]] = groups.get(i["group"], 0.0) + i["amount"]
            flags = ("P" if m.get("predicted") else " ") + (" " if m.get("matched", True) else "!")
            flags += "".join(x[0].upper() for x in m.get("prices", []))
            parts = " ".join(f"{g}={v:.2f}" for g, v in groups.items())
            print(
                f"{m['month']} {m.get('source', ''):10} {flags} total={sum(groups.values()):9.2f} {parts}"
            )
        for m in report["payout"]:
            print(f"{m['month']} payout     {sum(i['amount'] for i in m['items']):9.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
