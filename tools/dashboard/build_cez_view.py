"""Build the "ČEZ" view as a Dashboard Editor model view (VRM style blocks).

Usage: CEZ_PREFIX=sensor.cez_<place>_ build_cez_view.py view.json

Output is one view of the Dashboard Editor model (type `block` cards rendered by viewlib with
the vrm_head / vrm_details templates). JS bodies follow viewlib conventions: the renderer
adds dashTap and its helpers (n, f, st, u, cz) itself, so the bodies must not define those
names; local helpers use other names (so, fm, uu, ...). Entities read in charts are written
literally (states['...']) so button-card re-renders when they change.
"""

import json
import os
import re
import sys

# Entity ID prefix of the supply point sensors, e.g. sensor.cez_domov_
P = os.environ.get("CEZ_PREFIX", "sensor.cez_domov_")
# Account level entities (chart unit select, documents calendar, unread messages).
A_SELECT = os.environ.get("CEZ_SELECT", "select.muj_cez_jednotka_grafu")
A_CALENDAR = os.environ.get("CEZ_CALENDAR", "calendar.muj_cez_doklady")
A_MESSAGES = os.environ.get("CEZ_MESSAGES", "sensor.muj_cez_neprectene_zpravy")
# Export mode: all sections tagged with the data they need (integration template).
EXPORT = os.environ.get("CEZ_EXPORT") == "1"

# Local JS helpers (names must not clash with viewlib helpers n, f, st, u, cz).
JS = (
    "const id=(k)=>k;const st=(k)=>states[k];"
    "const f=(x,d=0)=>{const v=parseFloat(x);return isNaN(v)?'–':v.toLocaleString('cs-CZ',"
    "{minimumFractionDigits:d,maximumFractionDigits:d})};"
    "const num=(k,d=0)=>{const s=st(k);return s?f(s.state,d):'–'};"
    "const at=(k,a)=>{const s=st(k);return s?s.attributes[a]:undefined};"
    "const dt=(v)=>v&&v!=='unknown'&&v!=='unavailable'?String(v).slice(0,10).split('-').reverse().join('.'):'–';"
    "const u=(v,unit)=>`${v}<span class='u'>${unit}</span>`;"
    'const row=(k,l,v)=>`<div class=\'r\' data-tap=\'{"action":"more-info","entity":"${id(k)}"}\' '
    "onclick='dashTap(event,this)' ontouchstart='cezTs(event)' ontouchend='cezTe(event,this)' style='pointer-events:auto;cursor:pointer'><span class='l'>${l}</span><span>${v}</span></div>`;"
    # Touch: button-card swallows the click on touch devices; tap = touch without movement.
    "globalThis.cezTs=(ev)=>{const t=ev.changedTouches[0];globalThis.__cezT=[t.clientX,t.clientY]};"
    "globalThis.cezTe=(ev,el)=>{const t=ev.changedTouches[0],s=globalThis.__cezT||[1e9,1e9];"
    "if(Math.abs(t.clientX-s[0])+Math.abs(t.clientY-s[1])<10){ev.preventDefault();dashTap(ev,el)}};"
)
RENAME = {"st": "so", "f": "fm", "u": "uu"}
_RENAME_RE = re.compile(r"(?<![\w.$'\"])(st|f|u)(?=\(|=)")


_SHORT_KEY_RE = re.compile(r"\b(st|num|at|row|id)\('([a-z0-9_]+)'")


def rename(body: str) -> str:
    """Full entity IDs instead of short keys (so the editor check and button-card see them),
    and local helper names that do not clash with viewlib helpers."""
    body = _SHORT_KEY_RE.sub(lambda m: f"{m[1]}('{P}{m[2]}'", body)
    return _RENAME_RE.sub(lambda m: RENAME[m[1]], body)


def js(body: str) -> dict:
    return {"js": rename(JS + body)}


def heading(text: str, icon: str) -> dict:
    return {"type": "heading", "heading": text, "heading_style": "title", "icon": icon}


def head(entity: str, icon: str, title: str, extra_js: str, value_js: str) -> dict:
    return {
        "entity": entity,
        "icon": icon,
        "title": title,
        "extra": js(extra_js),
        "value": js(value_js),
    }


def details(rows_js: str) -> dict:
    return {"rows": js(rows_js)}


def graph(entity: str, hours: int) -> dict:
    return {
        "card": {
            "type": "custom:mini-graph-card",
            "hours_to_show": hours,
            "points_per_hour": 0.25,
            "line_width": 2,
            "height": 56,
            "animate": False,
            "group": True,
            "entities": [{"entity": entity, "color": "#8e8e93"}],
            "show": {
                "name": False,
                "icon": False,
                "state": False,
                "legend": False,
                "labels": False,
                "fill": "fade",
                "points": False,
            },
            "card_mod": {"style": "ha-card{background:none;border:none;box-shadow:none}"},
        }
    }


def stack(h: dict, *parts: dict) -> dict:
    """Editor model block: head + parts (rows / native card)."""
    return {
        "type": "block",
        **{k: h[k] for k in ("title", "icon", "entity", "value", "extra")},
        "parts": list(parts),
    }


billing = {
    "type": "grid",
    "cards": [
        heading("Vyúčtování", "mdi:scale-balance"),
        stack(
            head(
                P + "predikce_vyuctovani",
                "mdi:scale-balance",
                "Predikce vyúčtování",
                "const v=parseFloat(st('predikce_vyuctovani')?.state);"
                "return isNaN(v)?'':(v<0?'Přeplatek':'Doplatek')+' · do '+dt(at('predikce_vyuctovani','period_to'));",
                "const v=parseFloat(st('predikce_vyuctovani')?.state);return u(f(Math.abs(v)),'Kč');",
            ),
            graph(P + "predikce_vyuctovani", 720),
            details(
                "return row('predikovane_naklady_za_obdobi','Náklady za období',num('predikovane_naklady_za_obdobi')+' Kč')"
                "+row('predikovana_spotreba_za_obdobi','Spotřeba za období',num('predikovana_spotreba_za_obdobi')+' kWh')"
                "+row('konec_zuctovaciho_obdobi','Zúčtovací období',dt(at('konec_zuctovaciho_obdobi','period_from'))+' – '+dt(st('konec_zuctovaciho_obdobi')?.state))"
                "+row('doporucena_zaloha','Doporučená záloha',num('doporucena_zaloha')+' Kč')"
                "+row('aktualni_zaloha','Aktuální záloha',num('aktualni_zaloha')+' Kč');"
            ),
        ),
    ],
}

advances = {
    "type": "grid",
    "cards": [
        heading("Zálohy a platby", "mdi:cash-sync"),
        stack(
            head(
                P + "splatnost_pristi_zalohy",
                "mdi:calendar-clock",
                "Příští záloha",
                "return 'splatnost '+dt(st('splatnost_pristi_zalohy')?.state);",
                "return u(num('vyse_pristi_zalohy'),'Kč');",
            ),
            details(
                "const sipo=at('aktualni_zaloha','sipo');"
                "return row('splatnost_pristi_zalohy','Variabilní symbol',at('splatnost_pristi_zalohy','variable_symbol')||'–')"
                "+row('splatnost_pristi_zalohy','Účet ČEZ',at('splatnost_pristi_zalohy','bank_account')||'–')"
                "+row('aktualni_zaloha','Způsob platby',sipo===true?'SIPO':(sipo===false?'převodem':'–'))"
                "+row('nezaplacene_zalohy','Nezaplacené zálohy',num('nezaplacene_zalohy')+' Kč')"
                "+row('castka_po_splatnosti','Po splatnosti',num('castka_po_splatnosti')+' Kč')"
                "+row('posledni_platba','Poslední platba',num('posledni_platba')+' Kč · '+dt(at('posledni_platba','issue_date')))"
                "+row('posledni_faktura','Poslední faktura',num('posledni_faktura',2)+' Kč · '+dt(at('posledni_faktura','issue_date')));"
            ),
        ),
    ],
}

# Explicit build: CEZ_HDO=1 when the HA has the HDO sensors (the editor check rejects
# references to missing entities). Export: decided at runtime by the integration.
HDO_ON = os.environ.get("CEZ_HDO") == "1"
# Single tariff HA without the NT meter sensor: CEZ_NT=0 (the editor check rejects missing ids).
NT_ON = EXPORT or os.environ.get("CEZ_NT") != "0"
# Single tariff / no HDO: the price per kWh lives in the contract block (else in HDO).
PRICE_ROW = (
    "(st('aktualni_cena')&&!st('tarif_hdo')?row('aktualni_cena','Aktuální cena',num('aktualni_cena',2)+' Kč/kWh'):'')"
    if EXPORT
    else "''"
    if HDO_ON
    else "(st('aktualni_cena')?row('aktualni_cena','Aktuální cena',num('aktualni_cena',2)+' Kč/kWh'):'')"
)

contract = {
    "type": "grid",
    "cards": [
        heading("Smlouva a odběrné místo", "mdi:file-sign"),
        stack(
            head(
                P + "distribucni_sazba",
                "mdi:transmission-tower",
                "Distribuční sazba",
                "return 'jistič '+num('hlavni_jistic')+' A';",
                "const s=st('distribucni_sazba')?.state||'–';return s.split(' - ')[0];",
            ),
            details(
                "const desc=(st('distribucni_sazba')?.state||'').split(' - ').slice(1).join(' - ');"
                "return row('distribucni_sazba','Sazba',desc||'–')"
                "+row('produkt','Produkt',st('produkt')?.state||'–')"
                "+row('konec_smlouvy','Konec smlouvy',dt(st('konec_smlouvy')?.state))"
                "+row('datum_zmeny_ceny','Změna ceny',dt(st('datum_zmeny_ceny')?.state))"
                + (
                    "+row('stav_elektromeru',st('stav_elektromeru_nt')?'Stav elektroměru VT':'Stav elektroměru',"
                    "num('stav_elektromeru')+' kWh · '+dt(at('stav_elektromeru','reading_date')))"
                    # Dual tariff only: the NT sensor exists.
                    "+(st('stav_elektromeru_nt')?row('stav_elektromeru_nt','Stav elektroměru NT',"
                    "num('stav_elektromeru_nt')+' kWh · '+dt(at('stav_elektromeru_nt','reading_date'))):'')"
                    if NT_ON
                    else "+row('stav_elektromeru','Stav elektroměru',"
                    "num('stav_elektromeru')+' kWh · '+dt(at('stav_elektromeru','reading_date')))"
                )
                + ""
                "+row('spotreba_za_minule_obdobi','Minulé období',num('spotreba_za_minule_obdobi')+' kWh · '+num('naklady_za_minule_obdobi')+' Kč')"
                "+row('planovane_odstavky','Plánované odstávky',st('planovane_odstavky')?.state??'–')"
                "+" + PRICE_ROW + ""
                f"+row('{A_MESSAGES}','Nepřečtené zprávy',st('{A_MESSAGES}')?.state??'–')"
                "+row('ean','EAN',st('ean')?.state||'–')"
                "+row('cislo_elektromeru','Číslo elektroměru',st('cislo_elektromeru')?.state||'–')"
                "+row('cislo_smlouvy','Číslo smlouvy',st('cislo_smlouvy')?.state||'–')"
                "+row('zakaznicke_cislo','Zákaznické číslo',st('zakaznicke_cislo')?.state||'–')"
                "+row('posledni_aktualizace','Aktualizováno',(()=>{const v=st('posledni_aktualizace')?.state;"
                "if(!v||v==='unknown')return '–';const d=new Date(v);return d.toLocaleString('cs-CZ',{dateStyle:'short',timeStyle:'short'})})());"
            ),
        ),
    ],
}

# Gas point (export only): meter in m³, no circuit breaker / HDO / reading comparison.
GAS_ROWS_TAIL = (
    "+row('spotreba_za_minule_obdobi','Minulé období',num('spotreba_za_minule_obdobi')+' kWh · '+num('naklady_za_minule_obdobi')+' Kč')"
    "+row('planovane_odstavky','Plánované odstávky',st('planovane_odstavky')?.state??'–')"
    f"+row('{A_MESSAGES}','Nepřečtené zprávy',st('{A_MESSAGES}')?.state??'–')"
    "+row('ean','EAN',st('ean')?.state||'–')"
    "+row('cislo_plynomeru','Číslo plynoměru',st('cislo_plynomeru')?.state||'–')"
    "+row('cislo_smlouvy','Číslo smlouvy',st('cislo_smlouvy')?.state||'–')"
    "+row('zakaznicke_cislo','Zákaznické číslo',st('zakaznicke_cislo')?.state||'–')"
    "+row('posledni_aktualizace','Aktualizováno',(()=>{const v=st('posledni_aktualizace')?.state;"
    "if(!v||v==='unknown')return '–';const d=new Date(v);return d.toLocaleString('cs-CZ',{dateStyle:'short',timeStyle:'short'})})());"
)

contract_gas = {
    "type": "grid",
    "cards": [
        heading("Smlouva a odběrné místo", "mdi:file-sign"),
        stack(
            head(
                P + "stav_plynomeru",
                "mdi:meter-gas",
                "Stav plynoměru",
                "return 'odečet '+dt(at('stav_plynomeru','reading_date'));",
                "return u(num('stav_plynomeru'),'m³');",
            ),
            details(
                "return row('produkt','Produkt',st('produkt')?.state||'–')"
                "+row('distribucni_sazba','Distribuční sazba',st('distribucni_sazba')?.state||'–')"
                "+row('konec_smlouvy','Konec smlouvy',dt(st('konec_smlouvy')?.state))"
                "+row('datum_zmeny_ceny','Změna ceny',dt(st('datum_zmeny_ceny')?.state))"
                + GAS_ROWS_TAIL
            ),
        ),
    ],
}

gas_readings = {
    "type": "grid",
    "cards": [
        heading("Odečty plynoměru", "mdi:meter-gas"),
        stack(
            head(
                P + "stav_plynomeru",
                "mdi:fire",
                "Spotřeba mezi odečty",
                "const rs=at('stav_plynomeru','readings')||[];const r=rs[rs.length-1];"
                "const p=rs[rs.length-2];return r&&p&&r.consumption!=null?dt(p.date)+' – '+dt(r.date):'';",
                "const rs=at('stav_plynomeru','readings')||[];const r=rs[rs.length-1];"
                "return u(r&&r.consumption!=null?f(r.consumption):'–','m³');",
            ),
            details(
                "const rs=(at('stav_plynomeru','readings')||[]).slice().reverse().slice(0,12);"
                "const th=(t,r)=>`<th style='text-align:${r?'right':'left'};font-weight:400;color:var(--secondary-text-color);padding:7px 0 7px 12px'>${t}</th>`;"
                "const td=(t,r)=>`<td style='text-align:${r?'right':'left'};padding:7px 0 7px 12px;border-top:1px solid var(--divider-color);white-space:nowrap'>${t}</td>`;"
                "const sub=(t)=>`<div style='font-size:11px;color:var(--secondary-text-color)'>${t}</div>`;"
                "const all=at('stav_plynomeru','readings')||[];"
                "const body=rs.map(r=>{const first=all.indexOf(r)===0;"
                "const c=r.consumption!=null?f(r.consumption)+' m³':(first?'–':sub('nový plynoměr'));"
                "return '<tr>'+td(dt(r.date)+sub(r.reading_type||''))+td(f(r.value)+' m³',1)+td(c,1)+'</tr>'}).join('');"
                "return `<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:13px'>"
                "<tr>${th('Odečet')}${th('Stav',1)}${th('Spotřeba',1)}</tr>${body}</table></div>`"
                "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:6px 0;white-space:normal'>"
                "Plynoměr měří m³, portál účtuje kWh (přepočet podle spalného tepla).</div>`;"
            ),
        ),
    ],
}

HDO_JS = (
    "const H=st('tarif_hdo');const HA2=H?H.attributes:{};const LOWT=H?.state==='low';"
    "const NTC='var(--success-color,#43a047)';const VTC='#8e8e93';"
    "const mins=(x)=>{const p=String(x).split(':');return +p[0]*60+ +p[1]};"
    "const hm=(x)=>String(Math.floor(x/60)).padStart(2,'0')+':'+String(x%60).padStart(2,'0');"
    "const sw=()=>{const v=st('pristi_prepnuti_tarifu')?.state;if(!v||v==='unknown'||v==='unavailable')return null;return new Date(v)};"
    "const swt=(d)=>d?d.toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit'})"
    "+(d.toDateString()===new Date().toDateString()?'':' ('+d.toLocaleDateString('cs-CZ',{weekday:'short'})+')'):'–';"
)


def hdo_bar_js() -> str:
    """24 h bar per day: NT green, VT grey, marker at the current time; tooltip per segment."""
    return (
        "const bar=(lab,ivs,now)=>{const sg=[];let pos=0;"
        "(ivs||[]).forEach(iv=>{const [a,b]=iv.split('-').map(mins);if(a>pos)sg.push([pos,a,0]);sg.push([a,b,1]);pos=b});"
        "if(pos<1440)sg.push([pos,1440,0]);"
        "const cells=sg.map(([a,b,l])=>`<div title='${l?'NT':'VT'} ${hm(a)}–${hm(b)}' "
        "style='width:${(b-a)/14.4}%;background:${l?NTC:VTC};opacity:${l?1:.35}'></div>`).join('');"
        "const mk=now==null?'':`<div style='position:absolute;left:calc(${now/14.4}% - 1px);top:-4px;bottom:-4px;width:2px;"
        "border-radius:1px;background:var(--primary-text-color)'></div>`;"
        "return `<div style='display:flex;align-items:center;gap:10px;padding:7px 0'>"
        "<span style='width:40px;font-size:12px;color:var(--secondary-text-color)'>${lab}</span>"
        "<div style='position:relative;flex:1'><div style='display:flex;height:16px;border-radius:5px;overflow:hidden'>${cells}</div>${mk}</div></div>`};"
        "const axis=`<div style='display:flex;gap:10px;font-size:11px;color:var(--secondary-text-color)'><span style='width:40px'></span>"
        "<div style='flex:1;display:flex;justify-content:space-between'>${[0,6,12,18,24].map(h=>`<span>${h}</span>`).join('')}</div></div>`;"
        "const sw0=(c,t)=>`<span style='display:inline-block;width:10px;height:10px;border-radius:2px;background:${c};margin:0 5px 0 12px'></span>${t}`;"
    )


hdo = {
    "type": "grid",
    "column_span": 3,
    "cards": [
        heading("Tarif HDO a cena", "mdi:transmission-tower"),
        stack(
            head(
                P + "tarif_hdo",
                "mdi:transmission-tower",
                "Aktuální tarif",
                HDO_JS + "const d=sw();return d?(LOWT?'NT':'VT')+' do '+swt(d):'';",
                HDO_JS + "return H?u(LOWT?'NT':'VT',num('aktualni_cena',2)+' Kč/kWh'):'–';",
            ),
            details(
                HDO_JS
                + hdo_bar_js()
                + "const nw=new Date();const nowm=nw.getHours()*60+nw.getMinutes();"
                "const list=(a)=>(a&&a.length?a.map(x=>x.replace(/:00/g,'').replace('-','–')).join(', '):'celý den VT');"
                "return bar('Dnes',HA2.today,nowm)+bar('Zítra',HA2.tomorrow,null)+axis"
                "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:6px 0 4px'>${sw0(NTC,'nízký tarif (NT)')}"
                "${sw0('rgba(142,142,147,.35)','vysoký tarif (VT)')}</div>`"
                "+row('aktualni_cena','Aktuální cena',num('aktualni_cena',2)+' Kč/kWh')"
                "+row('aktualni_cena','Cena VT / NT',f(at('aktualni_cena','price_vt'),2)+' / '+f(at('aktualni_cena','price_nt'),2)+' Kč/kWh')"
                "+row('pristi_prepnuti_tarifu','Příští přepnutí',(()=>{const d=sw();return d?swt(d)+' na '+(LOWT?'VT':'NT'):'–'})())"
                "+row('tarif_hdo','NT dnes',f(HA2.low_hours_today,1)+' h')"
                "+row('tarif_hdo','Dnes NT',list(HA2.today))"
                "+row('tarif_hdo','Zítra NT',HA2.tomorrow?list(HA2.tomorrow):'–')"
                "+row('tarif_hdo','Signál HDO',(HA2.signal||'–')+' · rozpis do '+dt(HA2.schedule_until));"
            ),
        ),
    ],
}

periods_rows = (
    "const ps=(at('zuctovaci_obdobi','periods')||[]).slice().reverse();"
    "const th=(t,r)=>`<th style='text-align:${r?'right':'left'};font-weight:400;color:var(--secondary-text-color);padding:7px 0 7px 12px'>${t}</th>`;"
    "const td=(t,r)=>`<td style='text-align:${r?'right':'left'};vertical-align:top;padding:7px 0 7px 12px;border-top:1px solid var(--divider-color);white-space:nowrap'>${t}</td>`;"
    "const res=(s)=>s==null?'–':(s<0?`<span style='color:var(--success-color,#43a047)'>přeplatek ${f(-s)} Kč</span>`"
    ":`<span style='color:var(--error-color,#db4437)'>doplatek ${f(s)} Kč</span>`);"
    "const sub=(t)=>`<div style='font-size:11px;color:var(--secondary-text-color)'>${t}</div>`;"
    "const adv=(p)=>{const t=p.advances_total!=null?p.advances_total:p.paid;if(t==null)return '–';"
    "let x='';if(p.predicted&&p.paid!=null)x=sub(`zaplaceno ${f(p.paid)} Kč`"
    "+(p.advances_remaining_count?' · zbývá '+(p.advances_installment!=null?`${p.advances_remaining_count}× ${f(p.advances_installment)} Kč`"
    ":`${p.advances_remaining_count} plateb`)+` (${f(p.advances_remaining)} Kč)`:''));"
    "else if(!p.predicted&&p.paid!=null&&p.advances_total!=null&&Math.abs(p.advances_total-p.paid)>=1)"
    "x=sub(`platby ${f(p.paid)} Kč · ostatní ${f(p.advances_total-p.paid)} Kč`);"
    "return f(t)+' Kč'+x};"
    "const body=ps.map(p=>`<tr data-tap='{\"action\":\"more-info\",\"entity\":\"${id('zuctovaci_obdobi')}\"}' onclick='dashTap(event,this)' ontouchstart='cezTs(event)' ontouchend='cezTe(event,this)' style='pointer-events:auto;cursor:pointer'>`"
    "+td(`${dt(p.from)} – ${dt(p.to)}`+(p.predicted?\" <span style='color:var(--primary-color)'>predikce</span>\":''))"
    "+td(f(p.consumption_kwh)+' kWh',1)+td(f(p.cost)+' Kč',1)+td(adv(p),1)"
    "+td(res(p.settlement),1)+td(f(p.avg_price,2),1)+'</tr>').join('');"
    "return `<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:13px'>"
    "<tr>${th('Období')}${th('Spotřeba',1)}${th('Náklady',1)}${th('Zálohy za období',1)}${th('Vyúčtování',1)}${th('Kč/kWh',1)}</tr>"
    "${body}</table></div>`;"
)

periods = {
    "type": "grid",
    "column_span": 3,
    "cards": [
        heading("Zúčtovací období", "mdi:calendar-range"),
        stack(
            head(
                P + "zuctovaci_obdobi",
                "mdi:calendar-range",
                "Průměrná cena",
                "const ps=(at('zuctovaci_obdobi','periods')||[]).filter(p=>!p.predicted);"
                "return ps.length?'minulé období':'';",
                "const ps=(at('zuctovaci_obdobi','periods')||[]).filter(p=>!p.predicted);"
                "const p=ps[ps.length-1];return u(p?f(p.avg_price,2):'–','Kč/kWh');",
            ),
            details(periods_rows),
        ),
    ],
}

documents = {
    "type": "grid",
    "column_span": 3,
    "cards": [
        heading("Doklady", "mdi:file-document-multiple-outline"),
        {
            "type": "calendar",
            "initial_view": "dayGridMonth",
            "entities": [A_CALENDAR],
            "grid_options": {"columns": "full", "rows": 12},
        },
    ],
}

# --- Charts: HA reference sensor vs portal (data from the comparison sensor) ---------
SELECT = A_SELECT
COMPARISON = P + "odchylka_od_cez"

CH = (
    "const SVC=['select','select_option'].join('.');"
    f"const SEL='{SELECT}';const UN=(states['{SELECT}']||{{}}).state==='czk'?'czk':'kwh';"
    f"const UL=UN==='czk'?'Kč':'kWh';const CMP=states['{COMPARISON}'];const CA=CMP?CMP.attributes:{{}};"
    "const RS=!!CA.reference_sensor;"
    "const MN=['led','úno','bře','dub','kvě','čvn','čvc','srp','zář','říj','lis','pro'];"
    "const mlab=(ym)=>{const [y,m]=ym.split('-');return MN[+m-1]+' '+y.slice(2)};"
    'const pill=(o,t)=>`<span data-tap=\'{"action":"perform-action","perform_action":"${SVC}",'
    '"target":{"entity_id":"${SEL}"},"data":{"option":"${o}"}}\' onclick=\'dashTap(event,this)\' '
    "ontouchstart='cezTs(event)' ontouchend='cezTe(event,this)' "
    "style='pointer-events:auto;cursor:pointer;padding:2px 10px;border-radius:10px;margin-left:4px;${UN===o?"
    "'background:var(--primary-color);color:var(--text-primary-color,#fff)':'border:1px solid var(--divider-color)'}'>${t}</span>`;"
    "const pills=()=>pill('kwh','kWh')+pill('czk','Kč');"
    "const HA='var(--primary-color)';const CZ='#8e8e93';"
    "const hatch=(c)=>`background:repeating-linear-gradient(45deg,${c} 0 3px,transparent 3px 6px)`;"
    "const sty=(c,o)=>(o&&o.hatch?hatch(c):'background:'+c)+';'+(o&&o.dim?'opacity:.55;':'');"
    "globalThis.cezTip=(ev,el,show)=>{ev.stopPropagation();const box=el.closest('.czc');if(!box)return;"
    "const tipEl=box.querySelector('.czt');box.querySelectorAll('.czg').forEach(c=>c.style.background='');"
    "if(!show){tipEl.style.display='none';return}el.style.background='rgba(127,127,127,.15)';"
    "tipEl.innerHTML=decodeURIComponent(el.dataset.tip);tipEl.style.display='block';"
    "const r=box.getBoundingClientRect(),c=el.getBoundingClientRect(),w=tipEl.offsetWidth;"
    "tipEl.style.left=Math.min(Math.max(c.left-r.left+c.width/2-w/2,0),r.width-w)+'px'};"
    "const bar=(v,max,H,c,o)=>`<div style='flex:1;max-width:18px;"
    "height:${v?Math.max(2,Math.round(v/max*H)):0}px;${sty(c,o)}border-radius:2px 2px 0 0'></div>`;"
    "const sw=(c,o)=>`<span style='display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;${sty(c,o)}'></span>`;"
    "const chart=(groups,legend,H=150)=>{const max=Math.max(1,...groups.flatMap(g=>g.b.map(x=>x.v||0)));"
    "const cols=groups.map(g=>{const tt=`<div style='font-weight:500;margin-bottom:4px'>${g.h||g.l}</div>`"
    "+g.b.map(x=>`<div style='display:flex;align-items:center;justify-content:space-between;gap:12px'>"
    "<span>${sw(x.c,x.o)}${x.n}</span><span>${x.v==null?'–':f(x.v,UN==='czk'?0:1)+' '+UL}</span></div>`).join('')"
    "+(g.x||[]).map(e=>`<div style='color:var(--secondary-text-color);margin-top:2px'>${e}</div>`).join('');"
    "return `<div class='czg' data-tip='${encodeURIComponent(tt).replace(/'/g,\"%27\")}' onmouseenter='cezTip(event,this,1)' "
    "onmouseleave='cezTip(event,this,0)' onclick='cezTip(event,this,1)' onpointerdown='cezTip(event,this,1)' style='flex:1;min-width:0;display:flex;"
    "flex-direction:column;align-items:center;pointer-events:auto;cursor:default;border-radius:4px'>"
    "<div style='height:${H}px;width:100%;display:flex;align-items:flex-end;justify-content:center;gap:2px;"
    "border-bottom:1px solid var(--divider-color)'>${g.b.map(x=>bar(x.v,max,H,x.c,x.o)).join('')}</div>"
    "<div style='font-size:10px;color:var(--secondary-text-color);margin-top:4px;white-space:nowrap'>${g.l}</div>"
    "${g.s?`<div style='font-size:10px;color:var(--secondary-text-color)'>${g.s}</div>`:''}</div>`}).join('');"
    "const leg=legend.map(([c,t,o])=>`<span style='display:inline-flex;align-items:center;gap:5px;margin-right:14px;"
    "white-space:nowrap'><span style='width:10px;height:10px;border-radius:2px;${sty(c,o)}'></span>${t}</span>`).join('');"
    "return `<div class='czc' style='position:relative;padding-top:16px'><div style='position:absolute;top:0;left:0;font-size:10px;"
    "color:var(--secondary-text-color)'>max ${f(max)} ${UL}</div>"
    "<div class='czt' style='display:none;position:absolute;top:0;z-index:3;pointer-events:none;font-size:12px;"
    "white-space:nowrap;padding:8px 10px;border-radius:8px;background:var(--card-background-color,#1c1c1c);"
    "border:1px solid var(--divider-color);box-shadow:0 4px 12px rgba(0,0,0,.35)'></div>"
    "<div style='display:flex;gap:3px' onmouseleave='cezTip(event,this.querySelector(\".czg\"),0)'>${cols}</div></div>"
    "<div style='font-size:12px;color:var(--secondary-text-color);padding:10px 0 2px;line-height:1.8;white-space:normal'>${leg}</div>`;};"
    "const tip=(t,v)=>`${t}: ${f(v,UN==='czk'?0:1)} ${UL}`;"
    "const pct=(x)=>x==null?'–':(x>0?'+':'')+f(x,1)+' %';"
    "const val=(o,k)=>o?(UN==='czk'?o[k+'_cost']:o[k+'_kwh']):null;"
)


def chead(title: str, icon: str, value_js: str) -> dict:
    return head(COMPARISON, icon, title, CH + "return pills();", CH + value_js)


def cdetails(body: str) -> dict:
    return details(CH + body)


monthly = {
    "type": "grid",
    "column_span": 3,
    "cards": [
        heading("Spotřeba po měsících", "mdi:chart-bar"),
        stack(
            chead(
                "Predikce za období",
                "mdi:chart-bar",
                "const p=(CA.periods||[]).find(x=>x.predicted);"
                "const v=p?(val(p,'ha')??val(p,'cez')):null;return u(f(v),UL);",
            ),
            cdetails(
                "const ms=CA.months||[];const c=CA.current||{};"
                "const g=ms.map((m,i)=>({l:m.month.endsWith('-01')?mlab(m.month):MN[+m.month.slice(5)-1],b:["
                "{v:val(m,'cez'),c:CZ,n:'ČEZ'+(m.estimated?' (odhad)':''),o:{hatch:m.estimated}},"
                "...(RS?[{v:val(m,'ha'),c:HA,n:'HA'+(m.ha_partial?' (zatím)':''),o:{dim:m.ha_partial}}]:[])],h:mlab(m.month)+' ('+dt(m.from).slice(0,6)+'–'+dt(m.to).slice(0,6)+')',"
                "x:(m.ha_kwh!=null&&m.cez_kwh)?['HA vs ČEZ '+pct((m.ha_kwh-m.cez_kwh)/m.cez_kwh*100)]:[]}));"
                "return chart(g,[[CZ,'ČEZ – rozpis odečtů'],[CZ,'ČEZ – odhad do konce období',{hatch:1}],"
                "...(RS?[[HA,'HA naměřeno'],[HA,'HA – běžící měsíc',{dim:1}]]:[])])"
                "+(RS?row('odchylka_od_cez','ČEZ do posledního odečtu ('+dt(c.measured_until)+')',f(c.cez_measured_kwh)+' kWh')"
                "+row('odchylka_od_cez','HA za stejné období',f(c.ha_measured_kwh,1)+' kWh')"
                "+row('odchylka_od_cez','Odchylka HA od ČEZ',pct(c.diff_pct)):'');",
            ),
        ),
    ],
}

YOY_JS = (
    "const ps=CA.periods||[];const hm=CA.ha_months||[];const cur=ps.find(p=>p.predicted);"
    "const labels=[...new Set(hm.map(x=>x.period))].slice(-3);"
    "const pal=['#5a5a5e','#b0b0b5',HA];const col={};labels.forEach((l,i)=>{col[l]=pal[pal.length-labels.length+i]});"
    "const price=(l)=>{const p=ps.find(x=>x.label===l);return p&&p.cez_kwh?p.cez_cost/p.cez_kwh:null};"
    "const conv=(l,v)=>v==null?null:(UN==='czk'?(price(l)?v*price(l):null):v);"
)

yoy = {
    "type": "grid",
    "column_span": 3,
    "cards": [
        heading("Meziroční porovnání", "mdi:chart-timeline-variant"),
        stack(
            chead(
                "Letos vs loni",
                "mdi:chart-timeline-variant",
                YOY_JS + "if(!cur||labels.length<2)return '–';const prev=labels[labels.length-2];"
                "const done=hm.filter(x=>x.period===cur.label&&x.complete).map(x=>x.index);"
                "const sum=(l)=>hm.filter(x=>x.period===l&&done.includes(x.index)).reduce((a,x)=>a+x.kwh,0);"
                "const a=sum(cur.label),b=sum(prev);if(!b)return '–';"
                "return u(pct((a-b)/b*100).replace(' %',''),'% vs '+prev);",
            ),
            cdetails(
                YOY_JS
                + "const ms=CA.months||[];const start=cur?new Date(cur.from):null;const groups=[];"
                "for(let i=0;i<13;i++){const lab=start?MN[(start.getMonth()+i)%12]:String(i+1);"
                "const b=labels.map(l=>{const x=hm.find(y=>y.period===l&&y.index===i);let v=x?x.kwh:null;let est=false;"
                "if(cur&&l===cur.label&&!x){const m=ms[i];if(m&&m.estimated&&m.ha_kwh==null){v=m.cez_kwh;est=true}}"
                "v=conv(l,v);return {v,c:col[l],n:l+(est?' (odhad ČEZ)':'')+(x&&!x.complete?' (neúplné)':''),"
                "o:{hatch:est,dim:x&&!x.complete}}});groups.push({l:lab,b,h:lab+' – '+(i+1)+'. měsíc období'})}"
                "const leg=labels.map(l=>[col[l],'období '+l]);"
                "if(cur&&col[cur.label])leg.push([col[cur.label],'odhad ČEZ do konce',{hatch:1}]);"
                "return chart(groups,leg)+`<div style='font-size:12px;color:var(--secondary-text-color);padding:4px 0;white-space:normal'>"
                "Měsíce zúčtovacího období (první a poslední může být jen část měsíce). Kč = kWh × průměrná cena období."
                "</div>`;",
            ),
        ),
    ],
}

totals = {
    "type": "grid",
    "column_span": 2,
    "cards": [
        heading("Zúčtovací období celkem", "mdi:chart-box-outline"),
        stack(
            chead(
                "Celkem za období",
                "mdi:chart-box-outline",
                # With the HA reference sensor: deviation of the last period, else its total.
                "const done=(CA.periods||[]).filter(x=>!x.predicted);"
                "if(!RS){const q=done.pop();return q?u(f(val(q,'cez')),UL+' · '+q.label):'–'}"
                "const p=done.filter(x=>x.diff_pct!=null).pop();"
                "return p?u(pct(p.diff_pct).replace(' %',''),'% HA/ČEZ · '+p.label):'–';",
            ),
            cdetails(
                "const ps=CA.periods||[];"
                "const g=ps.map(p=>{const ok=p.ha_coverage==='full';return {l:p.label,s:p.diff_pct!=null?pct(p.diff_pct):'',"
                "h:'Období '+p.label+' ('+dt(p.from)+' – '+dt(p.to)+')',x:p.diff_pct!=null?['HA vs ČEZ '+pct(p.diff_pct)]:(p.ha_coverage==='partial'?['HA data jen za část období']:[]),"
                "b:[{v:val(p,'cez'),c:CZ,n:'ČEZ'+(p.predicted?' (predikce)':''),o:{hatch:p.predicted}},"
                "...(RS?[{v:ok?val(p,'ha'):null,c:HA,n:'HA'+(p.predicted?' (naměřeno + odhad)':''),"
                "o:{hatch:p.predicted}}]:[])]}});"
                "return chart(g,[[CZ,'ČEZ fakturováno'],...(RS?[[HA,'HA naměřeno']]:[]),[CZ,'predikce',{hatch:1}]],130)"
                "+(RS?`<div style='font-size:12px;color:var(--secondary-text-color);padding:4px 0;white-space:normal'>HA data od "
                "${dt(CA.ha_first_day)}; období bez úplných dat HA jsou jen za ČEZ.</div>`:'');",
            ),
        ),
    ],
}

check = {
    "type": "grid",
    "column_span": 1,
    "cards": [
        heading("Kontrola měření", "mdi:counter"),
        stack(
            head(
                COMPARISON,
                "mdi:counter",
                "HA vs elektroměr ČEZ",
                CH + "return 'do '+dt((CA.current||{}).measured_until);",
                CH + "return u(pct((CA.current||{}).diff_pct).replace(' %',''),'%');",
            ),
            cdetails(
                "const rs=(CA.readings||[]).slice().reverse();"
                "return rs.map(r=>{const w=Math.abs(r.diff_pct)>5;"
                "return row('odchylka_od_cez',dt(r.from)+' – '+dt(r.to),"
                "`${f(r.cez_kwh)} / ${f(r.ha_kwh,1)} kWh · <span style='color:${w?'var(--warning-color,#ffa600)':'inherit'}'>"
                "${pct(r.diff_pct)}</span>`)}).join('')"
                "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:6px 0;white-space:normal'>ČEZ / HA mezi odečty "
                "elektroměru (stav ke konci dne odečtu).</div>`;",
            ),
        ),
    ],
}

# --- Smart meter / PV (only when the prefixes are given) -----------------------------
# Entities of the consumption place (grid import/export) and of the production point.
G = os.environ.get("CEZ_GRID_PREFIX", "")
V = os.environ.get("CEZ_PROD_PREFIX", "")
GRID_DATE = G + "data_elektromeru_k"
UNIT_EXPR = f"const UN=(states['{SELECT}']||{{}}).state==='czk'?'czk':'kwh';"
assert UNIT_EXPR in CH


def fixed_unit(unit: str) -> str:
    """Chart helpers with a fixed unit (FVE charts do not follow the kWh/Kč switch)."""
    return CH.replace(UNIT_EXPR, f"const UN='{unit}';")


GJS = (
    f"const GS=states['{GRID_DATE}'];const GD=GS?GS.attributes:{{}};"
    "const EXP='#f4b400';const IMP='#8e8e93';"
    "const gnum=(e,d=0)=>{const s=states[e];return s?f(s.state,d):'–'};"
    "const gat=(e,a)=>{const s=states[e];return s?s.attributes[a]:undefined};"
)


def grid_sections() -> list[dict]:
    if not G:
        return []
    e = lambda k: G + k  # noqa: E731
    overview = stack(
        head(
            e("pretoky_do_site_tento_mesic"),
            "mdi:transmission-tower-export",
            "Přetoky do sítě",
            GJS + f"return 'data k '+dt(states['{GRID_DATE}']?.state);",
            GJS + f"return u(gnum('{e('pretoky_do_site_tento_mesic')}',1),'kWh');",
        ),
        details(
            GJS + "const cmp=(k)=>{const c=(GD[k]||[]).filter(x=>x.diff_pct!=null).pop();"
            "return c?mlabg(c.month)+': '+f(c.ha_kwh,0)+' / '+f(c.cez_kwh,0)+' kWh · '+pctg(c.diff_pct):'–'};"
            f"return row('{e('pretoky_do_site_tento_mesic')}','Přetoky minulý měsíc',f(gat('{e('pretoky_do_site_tento_mesic')}','last_month'),1)+' kWh')"
            f"+row('{e('pretoky_do_site_letos')}','Přetoky letos / loni',gnum('{e('pretoky_do_site_letos')}')+' / '+f(gat('{e('pretoky_do_site_letos')}','last_year'))+' kWh')"
            f"+row('{e('odber_ze_site_tento_mesic')}','Odběr ze sítě tento měsíc',gnum('{e('odber_ze_site_tento_mesic')}')+' kWh')"
            f"+row('{e('odber_ze_site_tento_mesic')}','Odběr minulý měsíc',f(gat('{e('odber_ze_site_tento_mesic')}','last_month'))+' kWh')"
            f"+row('{e('odber_ze_site_letos')}','Odběr letos / loni',gnum('{e('odber_ze_site_letos')}')+' / '+f(gat('{e('odber_ze_site_letos')}','last_year'))+' kWh')"
            f"+row('{GRID_DATE}','Odběr HA / ČEZ',cmp('import_comparison'))"
            f"+row('{GRID_DATE}','Přetoky HA / ČEZ',cmp('export_comparison'));",
        ),
    )
    sections = [
        {
            "type": "grid",
            "column_span": 1,
            "cards": [heading("Elektroměr", "mdi:meter-electric-outline"), overview],
            "_requires": ["grid"],
        }
    ]
    if V:
        payout = stack(
            head(
                V + "vykup_za_posledni_mesic",
                "mdi:cash-plus",
                "Výkup přetoků",
                GJS
                + f"const m=gat('{V}vykup_za_posledni_mesic','month');return m?'za '+mlabg(m):'';",
                GJS + f"return u(gnum('{V}vykup_za_posledni_mesic'),'Kč');",
            ),
            details(
                GJS
                + f"const ps=gat('{V}vykup_za_posledni_mesic','payouts')||[];const l=ps.filter(p=>p.spot_value!=null).pop();"
                f"const sy=states['{e('spotova_cena_vcera')}'];const sa=sy?sy.attributes:{{}};"
                f"return row('{V}vykup_letos','Výkup letos',gnum('{V}vykup_letos')+' Kč')"
                f"+row('{V}vykupni_cena','Výkupní cena (poslední měsíc)',gnum('{V}vykupni_cena',2)+' Kč/kWh')"
                f"+row('{V}vykup_za_posledni_mesic','Přetoky za spot ('+(l?mlabg(l.month):'–')+')',l?f(l.spot_value)+' Kč · '+f(l.spot_price_per_kwh,2)+' Kč/kWh':'–')"
                f"+row('{e('spotova_cena_vcera')}','Spotová cena včera',sy&&sy.state!=='unknown'?f(sy.state,2)+' Kč/kWh ('+f(sa.min,2)+' – '+f(sa.max,2)+')':'–');",
            ),
        )
        sections.append(
            {
                "type": "grid",
                "column_span": 1,
                "cards": [heading("Výkup přetoků", "mdi:solar-power-variant"), payout],
                "_requires": ["production"],
            }
        )

    monthly_grid = {
        "type": "grid",
        "column_span": 3,
        "cards": [
            heading("Odběr a přetoky po měsících", "mdi:chart-bar-stacked"),
            stack(
                head(
                    GRID_DATE,
                    "mdi:chart-bar-stacked",
                    "Elektroměr ČEZ",
                    GJS + "return 'posledních 13 měsíců';",
                    GJS + f"return u(gnum('{e('pretoky_do_site_letos')}'),'kWh přetoků letos');",
                ),
                details(
                    fixed_unit("kwh")
                    + GJS
                    + "const ic=GD.import_comparison||[],ec=GD.export_comparison||[];"
                    "const ms=(GD.months||[]).slice(-13);"
                    "const g=ms.map(m=>{const a=ic.find(x=>x.month===m.month),b=ec.find(x=>x.month===m.month);"
                    "const x=[];if(a)x.push('HA odběr '+f(a.ha_kwh,0)+' kWh ('+pct(a.diff_pct)+')');"
                    "if(b)x.push('HA přetoky '+f(b.ha_kwh,0)+' kWh ('+pct(b.diff_pct)+')');"
                    "return {l:m.month.endsWith('-01')?mlab(m.month):MN[+m.month.slice(5)-1],h:mlab(m.month)+' ('+m.days+' dní)',x,"
                    "b:[{v:m.import_kwh,c:IMP,n:'Odběr ze sítě'},{v:m.export_kwh,c:EXP,n:'Přetoky do sítě'}]}});"
                    "return chart(g,[[IMP,'Odběr ze sítě (elektroměr ČEZ)'],[EXP,'Přetoky do sítě (elektroměr ČEZ)']]);",
                ),
            ),
        ],
    }
    comparison_index = len(sections)
    monthly_grid["_requires"] = ["grid"]
    sections.append(monthly_grid)
    if V:
        sections.append(
            {
                "type": "grid",
                "column_span": 3,
                "_requires": ["production"],
                "cards": [
                    heading("Výkup po měsících", "mdi:cash-multiple"),
                    stack(
                        head(
                            V + "vykup_letos",
                            "mdi:cash-multiple",
                            "Výkup vs spot",
                            GJS + "return 'Kč za měsíc';",
                            GJS + f"return u(gnum('{V}vykup_letos'),'Kč letos');",
                        ),
                        details(
                            fixed_unit("czk")
                            + GJS
                            + f"const ps=(gat('{V}vykup_za_posledni_mesic','payouts')||[]).slice(-13);"
                            "const g=ps.map(p=>({l:p.month.endsWith('-01')?mlab(p.month):MN[+p.month.slice(5)-1],h:mlab(p.month),"
                            "x:[p.export_kwh!=null?'Přetoky '+f(p.export_kwh,1)+' kWh':'',p.price_per_kwh!=null?'Výkup '+f(p.price_per_kwh,2)+' Kč/kWh':'',"
                            "p.spot_price_per_kwh!=null?'Spot '+f(p.spot_price_per_kwh,2)+' Kč/kWh':''].filter(Boolean),"
                            "b:[{v:p.amount,c:EXP,n:'Vyplacený výkup'},{v:p.spot_value??null,c:IMP,n:'Přetoky za spotovou cenu'}]}));"
                            "return chart(g,[[EXP,'Vyplacený výkup'],[IMP,'Přetoky oceněné spotem']],130);",
                        ),
                    ),
                ],
            }
        )
    sections.insert(
        comparison_index,
        {
            "type": "grid",
            "column_span": 1 if V else 2,
            "_requires": ["grid"],
            "_span_without_production": 2,
            "cards": [
                heading("HA vs elektroměr ČEZ", "mdi:scale-unbalanced"),
                stack(
                    head(
                        GRID_DATE,
                        "mdi:scale-unbalanced",
                        "Elektroměr po měsících",
                        GJS + "return 'odběr · přetoky';",
                        GJS
                        + "const c=(GD.export_comparison||[]).filter(x=>x.diff_pct!=null).pop();"
                        "return c?u(pctg(c.diff_pct).replace(' %',''),'% přetoky'):'–';",
                    ),
                    details(
                        GJS + "const ic=GD.import_comparison||[],ec=GD.export_comparison||[];"
                        "const ms=(GD.months||[]).slice().reverse();"
                        "const w=(c)=>c&&c.diff_pct!=null?` <span style='font-size:11px;color:${Math.abs(c.diff_pct)>5?"
                        "'var(--warning-color,#ffa600)':'var(--secondary-text-color)'}'>(HA ${pctg(c.diff_pct)})</span>`:'';"
                        f"return ms.map(m=>row('{GRID_DATE}',mlabg(m.month)+(m.days<new Date(+m.month.slice(0,4),+m.month.slice(5),0).getDate()?' *':''),"
                        "f(m.import_kwh)+w(ic.find(x=>x.month===m.month))+' · '+f(m.export_kwh,1)+w(ec.find(x=>x.month===m.month))+' kWh')).join('')"
                        "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:6px 0;white-space:normal'>Odběr · přetoky podle "
                        "elektroměru ČEZ za všechny měsíce s daty; v závorce odchylka HA tam, kde má HA data (jen dny v obou zdrojích). "
                        "* = neúplný měsíc.</div>`;",
                    ),
                ),
            ],
        },
    )
    return sections


S_TODAY = os.environ.get("CEZ_SPOT_TODAY", "")
S_TOMORROW = os.environ.get("CEZ_SPOT_TOMORROW", "")
SPOT_INFO = G + "spotova_cena_vcera"


def price_unit() -> str:
    """Chart helpers for prices in CZK/kWh with two decimals."""
    ch = fixed_unit("price")
    for old, new in (
        ("const UL=UN==='czk'?'Kč':'kWh';", "const UL='Kč/kWh';"),
        ("f(x.v,UN==='czk'?0:1)", "f(x.v,2)"),
        ("max ${f(max)} ${UL}", "max ${f(max,2)} ${UL}"),
    ):
        assert old in ch, old
        ch = ch.replace(old, new)
    return ch


SJS = (
    f"const SY=states['{SPOT_INFO}'];const SA=SY?SY.attributes:{{}};"
    # Hourly points of one local day (off: 0 today, 1 tomorrow); spot sensors often carry
    # today and tomorrow together in their attributes.
    "const pts=(e,off=0)=>{const s=states[e];const d=new Date();d.setDate(d.getDate()+off);const ds=d.toDateString();"
    "return s?Object.entries(s.attributes)"
    ".filter(([k])=>/^\\d{4}-\\d\\d-\\d\\dT/.test(k)).map(([k,v])=>[new Date(k),Array.isArray(v)?v[1]:v])"
    ".filter(x=>x[0].toDateString()===ds).sort((a,b)=>a[0]-b[0]):[]};"
)


def spot_sections() -> list[dict]:
    if not G:
        return []
    today_tomorrow = {
        "type": "grid",
        "column_span": 3,
        "cards": [
            heading("Spotová cena dnes a zítra", "mdi:chart-bell-curve"),
            stack(
                head(
                    S_TODAY or SPOT_INFO,
                    "mdi:chart-bell-curve",
                    "Aktuální spotová cena",
                    GJS + SJS + f"const t=pts('{S_TODAY}').map(x=>x[1]);"
                    "return t.length?'dnes '+f(Math.min(...t),2)+' – '+f(Math.max(...t),2)+' Kč/kWh':'';",
                    GJS + SJS + f"const s=states['{S_TODAY}'];return s?u(f(s.state,2),'Kč/kWh'):"
                    "u(f(SA.average,2),'Kč/kWh včera');",
                ),
                details(
                    price_unit()
                    + GJS
                    + SJS
                    + f"const today=pts('{S_TODAY}',0),tom=pts('{S_TOMORROW}',1);const now=new Date();"
                    "const prof=SA.profile||[];const est=!tom.length;"
                    "const lab=(d,h)=>h%6===0?String(h):'';const g=[];"
                    "today.forEach(([t,v])=>{const h=t.getHours();const cur=h===now.getHours()&&t.toDateString()===now.toDateString();"
                    "g.push({l:lab(t,h),h:'Dnes '+h+':00',b:[{v,c:cur?EXP:HA,n:cur?'Teď':'Dnes'}],"
                    "x:cur?['aktuální hodina']:[]})});"
                    "if(!est){tom.forEach(([t,v])=>{const h=t.getHours();g.push({l:h===0?'zítra':lab(t,h),h:'Zítra '+h+':00',"
                    "b:[{v,c:IMP,n:'Zítra'}]})})}"
                    "else{prof.forEach((v,h)=>g.push({l:h===0?'zítra':lab(null,h),h:'Zítra '+h+':00 (odhad)',"
                    "b:[{v,c:IMP,n:'Odhad',o:{hatch:1}}],x:['průměr stejné hodiny za 7 dní']}))}"
                    "const leg=[[HA,'dnes'],[EXP,'aktuální hodina'],est?[IMP,'zítra – odhad (průměr 7 dní)',{hatch:1}]:[IMP,'zítra (OTE)']];"
                    "return (g.length?chart(g,leg,140):'')+`<div style='font-size:12px;color:var(--secondary-text-color);padding:4px 0;"
                    "white-space:normal'>${est?'Zítřejší ceny OTE zveřejňuje kolem 13:00; do té doby je zítřek jen odhad podle "
                    "posledních 7 dní.':'Zítřejší ceny jsou zveřejněné (OTE).'}</div>`;",
                ),
            ),
        ],
    }
    monthly_spot = {
        "type": "grid",
        "column_span": 3,
        "cards": [
            heading("Spotová cena po měsících", "mdi:chart-areaspline"),
            stack(
                head(
                    SPOT_INFO,
                    "mdi:chart-areaspline",
                    "Průměrná spotová cena",
                    GJS + SJS + "return 'včera '+f(SA.average,2)+' Kč/kWh';",
                    GJS
                    + SJS
                    + "const m=(SA.months||[]).slice(-1)[0];return m?u(f(m.avg,2),'Kč/kWh · '+mlabg(m.month)):'–';",
                ),
                details(
                    price_unit()
                    + GJS
                    + SJS
                    + (
                        f"const ps=gat('{V}vykup_za_posledni_mesic','payouts')||[];"
                        if V
                        else "const ps=[];"
                    )
                    + "const ms=(SA.months||[]).slice(-13);"
                    "const g=ms.map(m=>{const p=ps.find(x=>x.month===m.month)||{};return {l:m.month.endsWith('-01')?mlab(m.month):MN[+m.month.slice(5)-1],"
                    "h:mlab(m.month)+' (min '+f(m.min,2)+', max '+f(m.max,2)+')',b:[{v:m.avg,c:IMP,n:'Průměr spotu'},"
                    "{v:p.spot_price_per_kwh??null,c:EXP,n:'Spot vážený přetoky',o:{hatch:1}},{v:p.price_per_kwh??null,c:EXP,n:'Vyplacený výkup'}]}});"
                    "const rows=ms.slice().reverse().map(m=>{const p=ps.find(x=>x.month===m.month)||{};"
                    f"return row('{SPOT_INFO}',mlabg(m.month),f(m.avg,2)+' · '+(p.spot_price_per_kwh!=null?f(p.spot_price_per_kwh,2):'–')"
                    "+' · '+(p.price_per_kwh!=null?f(p.price_per_kwh,2):'–')+' Kč/kWh')}).join('');"
                    "return chart(g,[[IMP,'průměr spotu'],[EXP,'spot vážený přetoky',{hatch:1}],[EXP,'vyplacený výkup']],130)"
                    "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:8px 0 2px'>Měsíc: průměr spotu · spot vážený "
                    "přetoky · výkup</div>`+rows;",
                ),
            ),
        ],
    }
    today_tomorrow["_requires"] = ["grid"]
    monthly_spot["_requires"] = ["grid"]
    return [today_tomorrow, monthly_spot]


def yoy_meter() -> dict:
    """Year over year by calendar month from the ČEZ smart meter (import and export)."""
    return {
        "type": "grid",
        "column_span": 3,
        "cards": [
            heading("Meziroční porovnání", "mdi:chart-timeline-variant"),
            stack(
                head(
                    GRID_DATE,
                    "mdi:chart-timeline-variant",
                    "Odběr ze sítě po letech",
                    GJS + "return 'elektroměr ČEZ';",
                    GJS + "const ms=GD.months||[];const now=new Date();const y=now.getFullYear();"
                    "const sum=(yr)=>ms.filter(m=>m.month.startsWith(yr+'-')&&+m.month.slice(5)<=now.getMonth()+1)"
                    ".reduce((a,m)=>a+(m.import_kwh||0),0);const a=sum(y),b=sum(y-1);"
                    "return b?u(pctg((a-b)/b*100).replace(' %',''),'% vs '+(y-1)+' (stejné měsíce)'):'–';",
                ),
                details(
                    fixed_unit("kwh")
                    + GJS
                    + "const ms=GD.months||[];const years=[...new Set(ms.map(m=>m.month.slice(0,4)))].slice(-3);"
                    "const pal=['#5a5a5e','#b0b0b5',HA];const col={};years.forEach((yr,i)=>{col[yr]=pal[pal.length-years.length+i]});"
                    "const g=MN.map((lab,i)=>{const mm=String(i+1).padStart(2,'0');"
                    "const b=years.map(yr=>{const m=ms.find(x=>x.month===yr+'-'+mm);return {v:m?m.import_kwh:null,c:col[yr],n:yr+(m&&m.export_kwh!=null?' (přetoky '+f(m.export_kwh,0)+' kWh)':''),"
                    "o:{dim:m&&m.days<new Date(+yr,i+1,0).getDate()}}});return {l:lab,b,h:lab}});"
                    "return chart(g,years.map(yr=>[col[yr],'odběr '+yr]))+`<div style='font-size:12px;color:var(--secondary-text-color);"
                    "padding:4px 0;white-space:normal'>Odběr ze sítě podle elektroměru ČEZ po kalendářních měsících; světlejší = neúplný měsíc. "
                    "Přetoky v tooltipu.</div>`;",
                ),
            ),
        ],
    }


GJS += (
    "const MNG=['led','úno','bře','dub','kvě','čvn','čvc','srp','zář','říj','lis','pro'];"
    "const mlabg=(ym)=>{const [y,m]=String(ym).split('-');return MNG[+m-1]+' '+y.slice(2)};"
    "const pctg=(x)=>x==null?'–':(x>0?'+':'')+f(x,1)+' %';"
)


# --- 15 min profile (websocket muj_cez/profile, loaded when the section renders) -------
# Shared state of all cards of the page: data per month, selected month and week.
PJS = (
    f"const PE='{GRID_DATE}';"
    "const PC=globalThis.__cezPf=globalThis.__cezPf||{d:{},m:{},w:{},ld:{},cards:new Set()};PC.cards.add(this);"
    # requestUpdate() keeps the cached template results; setConfig re-evaluates them.
    "globalThis.cezPfR=()=>globalThis.__cezPf.cards.forEach(c=>{if(!c.isConnected){globalThis.__cezPf.cards.delete(c);return}"
    "try{c._config&&c.setConfig?c.setConfig(c._config):c.requestUpdate()}catch(e){}});"
    "globalThis.cezPfGo=(ev,el)=>{ev.stopPropagation();const C=globalThis.__cezPf,e=el.dataset.e;"
    "if(el.dataset.m){C.m[e]=el.dataset.m;C.w[e]=null}if(el.dataset.w)C.w[e]=+el.dataset.w;"
    # Today: forget the chosen month / week and load the newest data again.
    "if(el.dataset.today){delete C.m[e];C.w[e]=null;delete C.d[e+'|']}globalThis.cezPfR()};"
    "globalThis.cezPfTe=(ev,el)=>{const t=ev.changedTouches[0],s=globalThis.__cezT||[1e9,1e9];"
    "if(Math.abs(t.clientX-s[0])+Math.abs(t.clientY-s[1])<10){ev.preventDefault();globalThis.cezPfGo(ev,el)}};"
    # Tooltip of the charts: PC.t[entity|chart](x, y) gives {t: html, b: [x0, x1, y0, y1]} for the
    # pointer position (fractions of the chart); b is the highlighted cell or time line.
    "PC.t=PC.t||{};"
    "globalThis.cezPfTip=(ev,el,show)=>{ev.stopPropagation();const tp=el.querySelector('.czpt'),mk=el.querySelector('.czpl');"
    "const T=globalThis.__cezPf.t[el.dataset.e+'|'+el.dataset.k];const r=el.querySelector('svg').getBoundingClientRect();"
    "const h=show&&T&&r.width?T((ev.clientX-r.left)/r.width,(ev.clientY-r.top)/r.height):null;"
    "if(!h){tp.style.display='none';mk.style.display='none';return}"
    "const W=r.width,H=r.height,b=h.b;mk.style.display='block';mk.style.left=b[0]*W+'px';mk.style.width=Math.max(2,(b[1]-b[0])*W)+'px';"
    "mk.style.top=b[2]*H+'px';mk.style.height=Math.max(2,(b[3]-b[2])*H)+'px';tp.innerHTML=h.t;tp.style.display='block';"
    "const tw=tp.offsetWidth,th=tp.offsetHeight,mx=ev.clientX-r.left,my=ev.clientY-r.top;"
    "tp.style.left=Math.min(Math.max(mx-tw/2,0),Math.max(0,W-tw))+'px';tp.style.top=(my-th-14<0?my+18:my-th-14)+'px'};"
    "const PK=(m)=>PE+'|'+(m||'');"
    "const PLOAD=(m)=>{const k=PK(m),o=PC.d[k];if(PC.ld[k]||(o&&Date.now()-o.ts<6e5))return;PC.ld[k]=1;"
    "hass.callWS(Object.assign({type:'muj_cez/profile',entity_id:PE},m?{month:m}:{}))"
    ".then(r=>{const v={r,ts:Date.now()};PC.d[k]=v;if(r.month){PC.d[PK(r.month)]=v;if(!PC.m[PE])PC.m[PE]=r.month}})"
    ".catch(e=>{PC.d[k]={err:String((e&&e.message)||e),ts:Date.now()}}).finally(()=>{delete PC.ld[k];globalThis.cezPfR()})};"
    "const PM=PC.m[PE];PLOAD(PM);const POBJ=PC.d[PK(PM)]||(PM?null:PC.d[PK()]);const PD=POBJ&&POBJ.r;"
    "const MNL=['leden','únor','březen','duben','květen','červen','červenec','srpen','září','říjen','listopad','prosinec'];"
    "const WDL=['po','út','st','čt','pá','so','ne'];"
    "const IMB='#3b82f6';const EXB='#f4b400';"
    # Day arrays have 92 / 100 values on the days the clock changes: map them to 96 clock slots.
    "const P96=(a)=>{if(!a)return null;if(a.length===96)return a;const o=new Array(96).fill(null);"
    "a.forEach((v,i)=>{const c=a.length===92?(i<8?i:i+4):(i<12?i:i-4);if(v!=null)o[c]=(o[c]||0)+v});return o};"
    "const hm=(i)=>String(Math.floor(i/4)).padStart(2,'0')+':'+String(i%4*15).padStart(2,'0');"
    "const isoW=(dd)=>{const t=new Date(Date.UTC(dd.getFullYear(),dd.getMonth(),dd.getDate()));const dn=(t.getUTCDay()+6)%7;"
    "t.setUTCDate(t.getUTCDate()-dn+3);const y0=new Date(Date.UTC(t.getUTCFullYear(),0,4));"
    "return 1+Math.round(((t-y0)/864e5-3+((y0.getUTCDay()+6)%7))/7)};"
    # Month model: calendar days, weeks (Monday to Sunday, cut at the month edges), stats.
    "const PMOD=(()=>{if(!PD||!PD.month)return null;const y=+PD.month.slice(0,4),mo=+PD.month.slice(5);"
    "const byD={};(PD.days||[]).forEach(x=>{byD[x.date]=x});const nd=new Date(y,mo,0).getDate();const days=[];"
    "for(let i=1;i<=nd;i++){const dd=new Date(y,mo-1,i);const key=PD.month+'-'+String(i).padStart(2,'0');const x=byD[key]||{};"
    "days.push({i,dd,wd:(dd.getDay()+6)%7,w:isoW(dd),im:P96(x.import),ex:P96(x.export)})}"
    "const weeks=[];days.forEach(d=>{let w=weeks[weeks.length-1];if(!w||w.w!==d.w){w={w:d.w,days:[]};weeks.push(w)}w.days.push(d)});"
    "const st0=()=>({imp:0,exp:0,mi:null,me:null,nd:0});"
    "const acc=(s,d)=>{let has=0;['im','ex'].forEach(k=>{(d[k]||[]).forEach((v,q)=>{if(v==null)return;has=1;"
    "if(k==='im'){s.imp+=v;if(!s.mi||v>s.mi.v)s.mi={v,d,q}}else{s.exp+=v;if(!s.me||v>s.me.v)s.me={v,d,q}}})});if(has)s.nd++};"
    "weeks.forEach(w=>{w.s=st0();w.days.forEach(d=>acc(w.s,d))});const tot=st0();days.forEach(d=>acc(tot,d));"
    "return {y,mo,days,weeks,tot}})();"
    "const kwh=(wh,dg=1)=>f(wh/1000,dg);const kw=(o)=>o?f(o.v*4/1000,1)+' kW':'–';"
    "const mlong=(ym)=>MNL[+ym.slice(5)-1]+' '+ym.slice(0,4);"
)


def profile_body() -> str:
    """Details of the 15 min section: month switch, weeks table, heat map, typical day, week detail."""
    return (
        GJS
        + PJS
        + "const msg=(t)=>`<div style='padding:12px 0;color:var(--secondary-text-color);white-space:normal'>${t}</div>`;"
        "if(POBJ&&POBJ.err)return msg('15minutová data nejsou dostupná: '+POBJ.err);"
        "if(!PD)return msg('Načítám 15minutová data…');"
        "if(!PD.months.length)return msg('15minutová data se stahují z portálu ČEZ. První načtení celé historie trvá několik minut, "
        "pak se sekce naplní.');"
        "const M=PMOD;const ms=PD.months,mi=ms.indexOf(PD.month);"
        # Hover / touch tooltip: wrapper with the chart, highlight and tooltip box.
        "const hv=(k)=>`data-e='${PE}' data-k='${k}' onmousemove='cezPfTip(event,this,1)' onpointermove='cezPfTip(event,this,1)' "
        "onpointerdown='cezPfTip(event,this,1)' onmouseleave='cezPfTip(event,this,0)' onclick='event.stopPropagation()'`;"
        "const HVS='pointer-events:auto;cursor:crosshair;touch-action:pan-y;';"
        "const tipbox=`<div class='czpl' style='display:none;position:absolute;pointer-events:none;box-sizing:border-box;"
        "border:1px solid var(--primary-text-color);border-radius:1px'></div><div class='czpt' style='display:none;position:absolute;z-index:3;"
        "pointer-events:none;font-size:12px;line-height:1.6;white-space:nowrap;padding:8px 10px;border-radius:8px;"
        "background:var(--card-background-color,#1c1c1c);border:1px solid var(--divider-color);box-shadow:0 4px 12px rgba(0,0,0,.35)'></div>`;"
        "const dot=(c)=>`<span style='display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:${c}'></span>`;"
        "const tl=(c,t,v)=>`<div>${dot(c)}${t}: ${v==null?'bez dat':f(v/1000,2)+' kWh · '+f(v*4/1000,2)+' kW'}</div>`;"
        "const qt=(d,q)=>`<div style='font-weight:500'>${WDL[d.wd]} ${d.i}. ${M.mo}. ${hm(q)}–${hm(q+1)}</div>`;"
        "const tap=(attrs,inner,sty)=>`<span ${attrs} data-e='${PE}' onclick='cezPfGo(event,this)' ontouchstart='cezTs(event)' "
        "ontouchend='cezPfTe(event,this)' style='pointer-events:auto;cursor:pointer;${sty||''}'>${inner}</span>`;"
        "const arrow=(m,t)=>m?tap(`data-m='${m}'`,t,'padding:2px 12px;border-radius:10px;border:1px solid var(--divider-color)'):"
        "`<span style='padding:2px 12px;opacity:.3'>${t}</span>`;"
        "const nav=`<div style='display:flex;align-items:center;justify-content:center;gap:10px;padding:4px 0 10px;font-size:15px'>"
        "${arrow(ms[mi-1],'‹')}<span style='min-width:130px;text-align:center;font-weight:500'>${mlong(PD.month)}</span>"
        "${arrow(ms[mi+1],'›')}${tap(`data-today='1'`,'Dnes',`padding:2px 12px;border-radius:10px;font-size:13px;"
        "border:1px solid var(--divider-color);${mi===ms.length-1&&PC.w[PE]==null?'opacity:.45':''}`)}</div>`;"
        # Selected week: chosen one, else the last week with data.
        "const wl=M.weeks.filter(w=>w.s.nd);let sw=PC.w[PE];if(sw==null||!M.weeks.some(w=>w.w===sw))sw=wl.length?wl[wl.length-1].w:null;"
        "const lab=(w)=>{const a=w.days[0],b=w.days[w.days.length-1];return a.i===b.i?a.i+'. '+M.mo+'.':a.i+'.–'+b.i+'. '+M.mo+'.'};"
        "const when=(o)=>o?`<div style='font-size:10px;color:var(--secondary-text-color)'>${WDL[o.d.wd]} ${o.d.i}. ${hm(o.q)}</div>`:'';"
        "const TC='display:grid;grid-template-columns:minmax(78px,1.4fr) repeat(4,minmax(0,1fr));gap:4px;align-items:center;"
        "padding:5px 6px;border-radius:6px;font-size:12px';"
        "const cell=(v,x)=>`<div style='text-align:right'>${v}${x||''}</div>`;"
        "const hdr=`<div style='${TC};color:var(--secondary-text-color);font-size:11px'><div>Týden</div>${cell('Odběr kWh')}"
        "${cell('Přetok kWh')}${cell('Max odběr')}${cell('Max přetok')}</div>`;"
        "const rows=M.weeks.map(w=>{const s=w.s,sel=w.w===sw;"
        "const inner=`<div>${w.w}. <span style='color:var(--secondary-text-color)'>(${lab(w)})</span></div>`"
        "+(s.nd?cell(kwh(s.imp))+cell(kwh(s.exp))+cell(kw(s.mi),when(s.mi))+cell(kw(s.me),when(s.me)):cell('–')+cell('–')+cell('')+cell(''));"
        "return s.nd?tap(`data-w='${w.w}'`,inner,TC+';display:grid;'+(sel?'background:rgba(127,127,127,.15)':'')):`<div style='${TC};opacity:.5'>${inner}</div>`}).join('');"
        "const T=M.tot;const total=`<div style='${TC};border-top:1px solid var(--divider-color);border-radius:0;font-weight:500'>"
        "<div>Měsíc celkem</div>${cell(kwh(T.imp))}${cell(kwh(T.exp))}${cell(kw(T.mi),when(T.mi))}${cell(kw(T.me),when(T.me))}</div>`;"
        "const table=`<div style='margin-bottom:14px'>${hdr}${rows}${total}</div>`;"
        # Heat map: rows = days, columns = 96 quarter hours; import blue, export orange.
        "const q98=(k)=>{const v=M.days.flatMap(d=>(d[k]||[]).filter(x=>x>0)).sort((a,b)=>a-b);return v.length?v[Math.floor((v.length-1)*.98)]:1};"
        "const QI=q98('im'),QE=q98('ex');const RH=12,GP=4;let rects='',yy=0;const YS=M.days.map((d,r)=>{if(d.wd===0&&r)yy+=GP;const y=yy;yy+=RH;return y});const HH=yy;"
        "M.days.forEach((d,r)=>{const y0=YS[r];if(!d.im&&!d.ex){rects+=`<rect x='0' y='${y0}' width='96' height='${RH-1}' fill='rgba(127,127,127,.12)'/>`;return}"
        "for(let q=0;q<96;q++){const a=d.im?d.im[q]:null,b=d.ex?d.ex[q]:null;if(a==null&&b==null){rects+=`<rect x='${q}' y='${y0}' width='1' height='${RH-1}' fill='rgba(127,127,127,.12)'/>`;continue}"
        "const e=(b||0)>(a||0);const v=e?b:a;if(!v)continue;const op=Math.min(1,.12+.88*v/(e?QE:QI)).toFixed(2);"
        "rects+=`<rect x='${q}' y='${y0}' width='1.02' height='${RH-1}' fill='${e?EXB:IMB}' fill-opacity='${op}'/>`}"
        "});"
        "PC.t[PE+'|heat']=(x,y)=>{const q=Math.min(95,Math.max(0,Math.floor(x*96))),py=y*HH;const r=YS.findIndex(v=>py>=v&&py<v+RH);"
        "if(r<0)return null;const d=M.days[r];return {t:qt(d,q)+tl(IMB,'odběr',d.im?d.im[q]:null)+tl(EXB,'přetok',d.ex?d.ex[q]:null),"
        "b:[q/96,(q+1)/96,YS[r]/HH,(YS[r]+RH-1)/HH]}};"
        "const dl=M.days.map((d,r)=>`<div style='height:${RH}px;line-height:${RH}px;margin-top:${d.wd===0&&r?GP:0}px;font-size:9px;color:var(--secondary-text-color);"
        "white-space:nowrap;${d.wd>4?'font-weight:600':''}'>${WDL[d.wd]} ${d.i}.</div>`).join('');"
        "const ax=(lft)=>`<div style='position:relative;height:14px;margin-left:${lft}px;font-size:9px;color:var(--secondary-text-color)'>`"
        "+[0,6,12,18,24].map(h=>`<span style='position:absolute;left:${h/24*100}%;transform:translateX(${h===24?'-100%':h?'-50%':'0'})'>${h}</span>`).join('')+'</div>';"
        "const grad=(c,t,mx)=>`<span style='display:inline-flex;align-items:center;gap:6px;margin-right:14px;white-space:nowrap'>${t}"
        "<span style='width:60px;height:8px;border-radius:2px;background:linear-gradient(90deg,rgba(127,127,127,.12),${c})'></span>"
        "do ${f(mx*4/1000,1)} kW</span>`;"
        "const heat=`<div style='font-size:13px;font-weight:500;margin:4px 0 6px'>Měsíc po čtvrthodinách</div>"
        "<div style='display:flex;gap:6px'><div style='flex:0 0 40px'>${dl}</div>"
        "<div ${hv('heat')} style='${HVS}flex:1;min-width:0;position:relative'><svg viewBox='0 0 96 ${HH}' preserveAspectRatio='none' shape-rendering='crispEdges' "
        "style='display:block;width:100%;height:${HH}px'>${rects}</svg>${tipbox}</div></div>"
        "${ax(46)}<div style='font-size:11px;color:var(--secondary-text-color);padding:4px 0 14px;line-height:1.8;white-space:normal'>"
        "${grad(IMB,'odběr',QI)}${grad(EXB,'přetok',QE)}· mezera = nový týden · šedá = bez dat · hodnoty po najetí myší</div>`;"
        # Typical day: average kW per quarter hour for every week; the selected week highlighted.
        "const avg=(w,k)=>{const sm=new Array(96).fill(0),cn=new Array(96).fill(0);w.days.forEach(d=>(d[k]||[]).forEach((v,q)=>{if(v!=null){sm[q]+=v;cn[q]++}}));"
        "return sm.map((s,q)=>cn[q]?s/cn[q]*4/1000:null)};"
        "const lines=wl.map(w=>({w:w.w,im:avg(w,'im'),ex:avg(w,'ex')}));"
        "const LM=Math.max(.1,...lines.flatMap(l=>[...l.im,...l.ex].filter(v=>v!=null)));"
        "const CH0=150,mid=CH0/2;const path=(a,sg)=>{let p='',pen=0;a.forEach((v,q)=>{if(v==null){pen=0;return}"
        "p+=(pen?'L':'M')+(q+.5)+' '+(mid-sg*v/LM*(mid-4)).toFixed(1)+' ';pen=1});return p};"
        "const svgl=lines.map(l=>{const sel=l.w===sw;const at=sel?\"stroke-width='2.2'\":\"stroke-width='1' stroke-opacity='.3'\";"
        "return `<path d='${path(l.im,1)}' fill='none' stroke='${IMB}' ${at} vector-effect='non-scaling-stroke'/>"
        "<path d='${path(l.ex,-1)}' fill='none' stroke='${EXB}' ${at} vector-effect='non-scaling-stroke'/>`}).join('');"
        "const kv=(v)=>v==null?'–':f(v,2)+' kW';"
        "PC.t[PE+'|typ']=(x)=>{const q=Math.min(95,Math.max(0,Math.floor(x*96)));"
        "return {t:`<div style='font-weight:500'>${hm(q)}–${hm(q+1)} <span style='font-weight:400;color:var(--secondary-text-color)'>průměr týdne</span></div>`"
        "+lines.map(l=>`<div style='${l.w===sw?'font-weight:600':'opacity:.75'}'>týden ${l.w}: ${dot(IMB)}${kv(l.im[q])} · ${dot(EXB)}${kv(l.ex[q])}</div>`).join(''),"
        "b:[(q+.5)/96-.002,(q+.5)/96+.002,0,1]}};"
        "const typ=`<div style='font-size:13px;font-weight:500;margin:4px 0 2px'>Typický den po týdnech</div>"
        "<div style='font-size:10px;color:var(--secondary-text-color)'>průměrný výkon za čtvrthodinu, nahoře odběr, dole přetok · max ${f(LM,1)} kW</div>"
        "<div ${hv('typ')} style='${HVS}position:relative'><svg viewBox='0 0 96 ${CH0}' preserveAspectRatio='none' style='width:100%;height:${CH0}px;display:block'>"
        "<line x1='0' x2='96' y1='${mid}' y2='${mid}' stroke='var(--divider-color)' vector-effect='non-scaling-stroke'/>${svgl}</svg>${tipbox}</div>${ax(0)}"
        "<div style='font-size:11px;color:var(--secondary-text-color);padding:2px 0 14px;white-space:normal'>Zvýrazněný je týden ${sw??'–'}; "
        "jiný týden vyberete klepnutím v tabulce.</div>`;"
        # Week detail: all quarter hours of the selected week (days of this month).
        "const W=M.weeks.find(w=>w.w===sw);let det='';"
        "if(W){const DW=W.days;const NQ=DW.length*96;const DM=Math.max(.1,...DW.flatMap(d=>[...(d.im||[]),...(d.ex||[])].filter(v=>v!=null).map(v=>v*4/1000)));"
        "const DH=160,dm=DH/2;let bars='';DW.forEach((d,j)=>{for(let q=0;q<96;q++){const x=j*96+q;"
        "const a=d.im?d.im[q]:null,b=d.ex?d.ex[q]:null;"
        "if(a){const h=a*4/1000/DM*(dm-2);bars+=`<rect x='${x}' y='${(dm-h).toFixed(1)}' width='1' height='${h.toFixed(1)}' fill='${IMB}'/>`}"
        "if(b){const h=b*4/1000/DM*(dm-2);bars+=`<rect x='${x}' y='${dm}' width='1' height='${h.toFixed(1)}' fill='${EXB}'/>`}}"
        "if(j)bars+=`<rect x='${j*96}' y='0' width='.6' height='${DH}' fill='var(--divider-color)'/>`});"
        "PC.t[PE+'|det']=(x)=>{const i=Math.min(NQ-1,Math.max(0,Math.floor(x*NQ)));const d=DW[Math.floor(i/96)],q=i%96;"
        "return {t:qt(d,q)+tl(IMB,'odběr',d.im?d.im[q]:null)+tl(EXB,'přetok',d.ex?d.ex[q]:null),b:[i/NQ,(i+1)/NQ,0,1]}};"
        "const dlab=DW.map(d=>`<div style='flex:1;text-align:center;font-size:10px;color:var(--secondary-text-color);white-space:nowrap'>${WDL[d.wd]} ${d.i}.</div>`).join('');"
        "const drow=DW.map(d=>{const s={imp:0,exp:0,mi:null,me:null,nd:0};['im','ex'].forEach(k=>(d[k]||[]).forEach((v,q)=>{if(v==null)return;"
        "if(k==='im'){s.imp+=v;if(!s.mi||v>s.mi.v)s.mi={v,d,q}}else{s.exp+=v;if(!s.me||v>s.me.v)s.me={v,d,q}}}));"
        "const has=d.im||d.ex;return `<div style='${TC}'><div>${WDL[d.wd]} ${d.i}. ${M.mo}.</div>`+(has?cell(kwh(s.imp))+cell(kwh(s.exp))"
        "+cell(kw(s.mi),s.mi?`<div style='font-size:10px;color:var(--secondary-text-color)'>${hm(s.mi.q)}</div>`:'')"
        "+cell(kw(s.me),s.me?`<div style='font-size:10px;color:var(--secondary-text-color)'>${hm(s.me.q)}</div>`:''):cell('–')+cell('–')+cell('')+cell(''))+'</div>'}).join('');"
        "det=`<div style='font-size:13px;font-weight:500;margin:4px 0 2px'>Týden ${W.w} (${lab(W)}) po čtvrthodinách</div>"
        "<div style='font-size:10px;color:var(--secondary-text-color)'>nahoře odběr, dole přetok · max ${f(DM,1)} kW</div>"
        "<div ${hv('det')} style='${HVS}position:relative'><svg viewBox='0 0 ${NQ} ${DH}' preserveAspectRatio='none' shape-rendering='crispEdges' "
        "style='width:100%;height:${DH}px;display:block'><rect x='0' y='${dm}' width='${NQ}' height='.6' fill='var(--divider-color)'/>${bars}</svg>${tipbox}</div>"
        "<div style='display:flex'>${dlab}</div><div style='margin-top:8px'>${hdr.replace('Týden','Den')}${drow}</div>`}"
        "return `<div style='text-align:left'>`+nav+table+heat+typ+det+`<div style='font-size:12px;color:var(--secondary-text-color);padding:8px 0 2px;white-space:normal'>"
        "15minutové hodnoty elektroměru z portálu ČEZ Distribuce (k dispozici den zpětně). Max = průměrný výkon za čtvrthodinu "
        "(kWh × 4).</div></div>`;"
    )


def profile_section() -> dict:
    return {
        "type": "grid",
        "column_span": 3,
        "_requires": ["grid"],
        "cards": [
            heading("Průběh po 15 minutách", "mdi:chart-timeline-variant"),
            stack(
                head(
                    GRID_DATE,
                    "mdi:chart-timeline-variant",
                    "Odběr a přetoky po čtvrthodinách",
                    GJS
                    + PJS
                    + "return PD&&PD.month?mlong(PD.month)+(PMOD?' · přetoky '+kwh(PMOD.tot.exp)+' kWh':''):'';",
                    GJS + PJS + "return PMOD?u(kwh(PMOD.tot.imp),'kWh odběr'):'–';",
                ),
                details(profile_body()),
            ),
        ],
    }


# --- Price breakdown view, own tab (websocket muj_cez/prices) --------------------------------
PRICES_PATH = "cez-ceny"
PRICE_ENTITY = P + "zuctovaci_obdobi"
# Shared state, data load and the selected period (month / quarter / year, index, VAT).
RJS = (
    "const RE='" + PRICE_ENTITY + "';"
    "const RC=globalThis.__cezPr=globalThis.__cezPr||{d:{},s:{},ld:{},cards:new Set()};RC.cards.add(this);"
    "globalThis.cezPrR=()=>globalThis.__cezPr.cards.forEach(c=>{if(!c.isConnected){globalThis.__cezPr.cards.delete(c);return}"
    "try{c._config&&c.setConfig?c.setConfig(c._config):c.requestUpdate()}catch(e){}});"
    "globalThis.cezPrGo=(ev,el)=>{ev.stopPropagation();const C=globalThis.__cezPr,ds=el.dataset,S=C.s[ds.e]=C.s[ds.e]||{};"
    "if(ds.mode){S.mode=ds.mode;S.i=null}if(ds.i)S.i=+ds.i;if(ds.vat)S.vat=ds.vat==='1';globalThis.cezPrR()};"
    "globalThis.cezPrTe=(ev,el)=>{const t=ev.changedTouches[0],s=globalThis.__cezT||[1e9,1e9];"
    "if(Math.abs(t.clientX-s[0])+Math.abs(t.clientY-s[1])<10){ev.preventDefault();globalThis.cezPrGo(ev,el)}};"
    # Loaded again after 10 min or when the invoices were checked (sensor attribute).
    "const RV=((hass.states[RE]||{}).attributes||{}).invoices_updated||'';"
    "const RLOAD=()=>{const o=RC.d[RE];if(RC.ld[RE]||(o&&o.v===RV&&Date.now()-o.ts<6e5))return;RC.ld[RE]=1;"
    "hass.callWS({type:'muj_cez/prices',entity_id:RE}).then(r=>{RC.d[RE]={r,v:RV,ts:Date.now()}})"
    ".catch(e=>{RC.d[RE]={err:String((e&&e.message)||e),code:e&&e.code,v:RV,ts:Date.now()}}).finally(()=>{delete RC.ld[RE];globalThis.cezPrR()})};"
    "RLOAD();const RO=RC.d[RE],RD=RO&&RO.r,RS=RC.s[RE]=RC.s[RE]||{};const MODE=RS.mode||'m',VAT=RS.vat!==false;"
    "const MNL=['leden','únor','březen','duben','květen','červen','červenec','srpen','září','říjen','listopad','prosinec'];"
    "const MNS=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII'];"
    "const pkey=(ym)=>MODE==='y'?ym.slice(0,4):MODE==='q'?ym.slice(0,4)+'-Q'+(Math.floor((+ym.slice(5)-1)/3)+1):ym;"
    "const plab=(k)=>MODE==='y'?'rok '+k:MODE==='q'?k.slice(6)+'. čtvrtletí '+k.slice(0,4):MNL[+k.slice(5)-1]+' '+k.slice(0,4);"
    "const psh=(k)=>MODE==='y'?k:MODE==='q'?k.slice(5)+'/'+k.slice(2,4):MNS[+k.slice(5)-1]+(k.slice(5)==='01'?' '+k.slice(2,4):'');"
    # Periods: items of the months merged by kind; flags of the months.
    "const RP=(()=>{if(!RD)return null;const ps={};const add=(m,pay)=>{const k=pkey(m.month);"
    "const p=ps[k]=ps[k]||{k,it:{},pay:{},src:new Set(),pred:false,mis:false,pl:false};"
    "if(!pay){p.src.add(m.source);p.pred=p.pred||!!m.predicted;p.mis=p.mis||m.matched===false;p.pl=p.pl||(m.prices||[]).some(x=>x!=='invoice')}"
    "m.items.forEach(i=>{const t=pay?p.pay:p.it;const x=t[i.kind]=t[i.kind]||{kind:i.kind,group:i.group,name:i.name,unit:i.unit,q:0,a:0,v:0,est:false};"
    "x.q+=i.quantity;x.a+=i.amount;x.v+=i.vat;x.est=x.est||i.estimated})};"
    "RD.months.forEach(m=>add(m,false));(RD.payout||[]).forEach(m=>add(m,true));"
    "return Object.values(ps).filter(p=>Object.keys(p.it).length||Object.keys(p.pay).length).sort((a,b)=>a.k<b.k?-1:1)})();"
    "const NOWK=pkey(new Date().toISOString().slice(0,7));"
    "let SI=RS.i;if(RP&&RP.length&&(SI==null||SI>=RP.length)){SI=RP.findIndex(p=>p.k===NOWK);if(SI<0)SI=RP.length-1}"
    "const SP=RP&&RP.length?RP[SI]:null;"
    "const val=(x)=>VAT?x.a+x.v:x.a;const tot=(p)=>Object.values(p.it).reduce((s0,x)=>s0+val(x),0);"
    "const GRP={supplier:['Obchodní část (dodavatel)','#3b82f6'],distribution:['Distribuční část (regulované ceny)','#f4b400'],"
    "tax:['Daň z elektřiny','#a855f7'],simulation:['Souhrn ze simulace (bez rozpadu)','#8e8e93'],other:['Ostatní','#8e8e93']};"
    "const GORD=['supplier','distribution','tax','simulation','other'];"
)


def prices_body() -> str:
    return (
        RJS
        + "const msg=(t)=>`<div style='padding:12px 0;color:var(--secondary-text-color);white-space:normal'>${t}</div>`;"
        "if(RO&&RO.code==='disabled')return msg('Cenový rozpad je vypnutý v nastavení integrace (Nastavení → Zařízení a služby → Můj ČEZ → Konfigurovat).');"
        "if(RO&&RO.err)return msg('Cenový rozpad není dostupný: '+RO.err);"
        "if(!RD)return msg('Načítám cenový rozpad…');"
        "if(!SP)return msg('Faktury se stahují z portálu ČEZ. První načtení historie trvá několik minut, pak se sekce naplní.');"
        "const tap=(a,inner,sty)=>`<span ${a} data-e='${RE}' onclick='cezPrGo(event,this)' ontouchstart='cezTs(event)' "
        "ontouchend='cezPrTe(event,this)' style='pointer-events:auto;cursor:pointer;${sty||''}'>${inner}</span>`;"
        "const pill=(a,t,on)=>tap(a,t,'padding:2px 12px;border-radius:10px;font-size:13px;border:1px solid var(--divider-color);'"
        "+(on?'background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:var(--primary-color)':''));"
        "const arrow=(i,t)=>i>=0&&i<RP.length?tap(`data-i='${i}'`,t,'padding:2px 12px;border-radius:10px;border:1px solid var(--divider-color)')"
        ":`<span style='padding:2px 12px;opacity:.3'>${t}</span>`;"
        "const ctl=`<div style='display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:10px;padding:4px 0 10px'>"
        "<div style='display:flex;gap:4px'>${pill(`data-mode='m'`,'Měsíc',MODE==='m')}${pill(`data-mode='q'`,'Kvartál',MODE==='q')}"
        "${pill(`data-mode='y'`,'Rok',MODE==='y')}</div><div style='display:flex;align-items:center;gap:8px'>${arrow(SI-1,'‹')}"
        "<span style='min-width:150px;text-align:center;font-weight:500;font-size:15px'>${plab(SP.k)}</span>${arrow(SI+1,'›')}</div>"
        "<div style='display:flex;gap:4px'>${pill(`data-vat='0'`,'bez DPH',!VAT)}${pill(`data-vat='1'`,'s DPH',VAT)}</div></div>`;"
        "const chip=(t,c)=>`<span style='font-size:11px;padding:1px 8px;border-radius:8px;border:1px solid ${c};color:${c};white-space:nowrap'>${t}</span>`;"
        "const IT=Object.values(SP.it);const src=SP.src;"
        "const chips=[src.has('invoice')||src.has('mixed')?chip('vyúčtováno','#22c55e'):'',"
        "src.has('simulation')||src.has('mixed')?chip('simulace ČEZ','#3b82f6'):'',SP.pred?chip('predikce','#f4b400'):'',"
        "IT.some(x=>x.est)?chip('≈ rozpočteno do období','#8e8e93'):'',SP.pl?chip('ceny z ceníku produktu','#a855f7'):'',SP.mis?chip('ceny nesouhlasí, bez rozpadu','#ef4444'):'']"
        ".filter(Boolean).join(' ');"
        "const dot=(c)=>`<span style='display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:${c}'></span>`;"
        # History columns (12 periods around the selected one), click selects.
        "const W0=Math.max(0,Math.min(SI-8,RP.length-12)),win=RP.slice(W0,W0+12);const mx=Math.max(...win.map(tot),1);"
        "const cols=win.map((p,j)=>{const i=W0+j,g={};Object.values(p.it).forEach(x=>{g[x.group]=(g[x.group]||0)+val(x)});"
        "const sg=GORD.filter(k=>g[k]>0).map(k=>`<div style='height:${g[k]/mx*100}%;background:${GRP[k][1]}'></div>`).reverse().join('');"
        "return tap(`data-i='${i}'`,`<div style='height:110px;display:flex;flex-direction:column;justify-content:flex-end;border-radius:3px;"
        "overflow:hidden;${p.pred?'opacity:.55;':''}${i===SI?'box-shadow:0 0 0 2px var(--primary-text-color);':''}'>${sg}</div>"
        "<div style='font-size:10px;text-align:center;color:var(--secondary-text-color);margin-top:4px;white-space:nowrap;overflow:hidden'>${psh(p.k)}</div>`,"
        "'flex:1;min-width:0;display:block')}).join('');"
        "const leg=GORD.filter(k=>RP.some(p=>Object.values(p.it).some(x=>x.group===k))).map(k=>`<span>${dot(GRP[k][1])}${GRP[k][0]}</span>`).join('');"
        "const chart=`<div style='display:flex;gap:4px;align-items:flex-end;margin:4px 0'>${cols}</div>"
        "<div style='display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11px;color:var(--secondary-text-color);margin-bottom:8px'>${leg}</div>`;"
        # Items table by group.
        "const T=tot(SP),gs={};IT.forEach(x=>{gs[x.group]=(gs[x.group]||0)+val(x)});"
        "const qty=(x)=>x.unit==='MWh'?f(x.q*1000,0)+' kWh':f(x.q,2)+' měs.';"
        "const up=(x,a)=>!x.q?'–':x.unit==='MWh'?f(a/(x.q*1000),3)+' Kč/kWh':f(a/x.q,2)+' Kč/měs.';"
        "const TC='display:grid;grid-template-columns:minmax(0,2.3fr) minmax(0,1fr) minmax(0,1.2fr) minmax(0,1fr);gap:6px;align-items:baseline;padding:5px 0;font-size:12px;text-align:left';"
        "const cell=(v)=>`<div style='text-align:right;white-space:nowrap'>${v}</div>`;"
        "const line=(x,a)=>`<div style='${TC};border-top:1px solid var(--divider-color)'><div style='white-space:normal;overflow-wrap:anywhere'>${x.name}${x.unit==='month'?"
        "` <span style='font-size:10px;color:var(--secondary-text-color)'>stálá</span>`:''}${x.est?` <span style='color:var(--secondary-text-color)'>≈</span>`:''}</div>"
        "${cell(qty(x))}${cell(up(x,a))}${cell(f(a,2)+' Kč')}</div>`;"
        "const hdr=`<div style='${TC};color:var(--secondary-text-color);font-size:11px'><div>Položka</div>${cell('Množství')}"
        "${cell('Jedn. cena '+(VAT?'s DPH':'bez DPH'))}${cell('Částka')}</div>`;"
        "const groups=GORD.filter(g=>IT.some(x=>x.group===g)).map(g=>{const xs=IT.filter(x=>x.group===g)"
        ".sort((a,b)=>(a.unit===b.unit?0:a.unit==='MWh'?-1:1));"
        "return `<div style='display:flex;justify-content:space-between;gap:8px;margin-top:12px;font-weight:500;font-size:13px'>"
        "<span>${dot(GRP[g][1])}${GRP[g][0]}</span><span>${f(gs[g],2)} Kč · ${!T?0:gs[g]/T<.01?'<1':f(gs[g]/T*100,0)} %</span></div>"
        "${xs.map(x=>line(x,val(x))).join('')}`}).join('');"
        "const sbar=`<div style='display:flex;height:8px;border-radius:4px;overflow:hidden;margin:10px 0 2px'>"
        "${GORD.filter(g=>gs[g]>0).map(g=>`<div style='width:${gs[g]/T*100}%;background:${GRP[g][1]}'></div>`).join('')}</div>`;"
        # Totals: fixed vs consumption, average price, VAT.
        "const r2=(l,v)=>`<div class='r'><span class='l'>${l}</span><span>${v}</span></div>`;"
        "const fixd=IT.filter(x=>x.unit==='month').reduce((s0,x)=>s0+val(x),0);"
        "const kwhs=IT.filter(x=>/^(energy|sim_vt|sim_nt)/.test(x.kind)).reduce((s0,x)=>s0+x.q*1000,0);"
        "const A=IT.reduce((s0,x)=>s0+x.a,0),V=IT.reduce((s0,x)=>s0+x.v,0);"
        "const sums=`<div style='margin-top:14px'>${r2('Spotřeba',f(kwhs,0)+' kWh')}"
        "${r2('Platby za spotřebu',f(T-fixd,2)+' Kč')}${r2('Stálé platby (nezávislé na spotřebě)',f(fixd,2)+' Kč')}"
        "${r2('Průměrná cena za kWh vč. stálých plateb',kwhs?f(T/kwhs,2)+' Kč/kWh':'–')}"
        "${r2('Celkem bez DPH',f(A,2)+' Kč')}${r2('DPH',f(V,2)+' Kč')}${r2('<b>Celkem s DPH</b>','<b>'+f(A+V,2)+' Kč</b>')}</div>`;"
        # Payout (production point).
        "const PY=Object.values(SP.pay);const pay=PY.length?`<div style='display:flex;justify-content:space-between;margin-top:14px;font-weight:500;font-size:13px'>"
        "<span>${dot('#22c55e')}Výkup elektřiny (přetoky)</span><span>${f(PY.reduce((s0,x)=>s0+x.a+x.v,0),2)} Kč</span></div>"
        "${PY.map(x=>line(x,x.a+x.v)).join('')}`:'';"
        # Documents of the period.
        "const pr=(k)=>{if(MODE==='y')return[k+'-01-01',k+'-12-31'];if(MODE==='q'){const q=+k.slice(6),y=k.slice(0,4);"
        "return[y+'-'+String(q*3-2).padStart(2,'0')+'-01',y+'-'+String(q*3).padStart(2,'0')+'-31']}return[k+'-01',k+'-31']};"
        "const [p0,p1]=pr(SP.k);const inv=(RD.invoices||[]).filter(x=>x.period_from&&x.period_from<=p1&&x.period_to>=p0);"
        "const SRC={csv:'datový soubor',pdf:'PDF',payout:'výkup'};"
        "const docs=inv.length?`<div style='margin-top:12px;font-size:11px;color:var(--secondary-text-color);white-space:normal'>Doklady: "
        "${inv.map(x=>`<span style='${x.replaced_by&&!x.partial?'text-decoration:line-through;opacity:.6':''}'>${x.number} (${dt(x.period_from)} – ${dt(x.period_to)}, ${SRC[x.source]||x.source}${x.corrective?', opravná':''}${x.replaced_by?(x.partial?', část nahrazena ':', nahrazena ')+x.replaced_by:''})</span>`).join(' · ')}</div>`:'';"
        "const note=`<div style='margin-top:8px;font-size:11px;color:var(--secondary-text-color);white-space:normal'>Položky a jednotkové ceny "
        "z vyúčtování ČEZ; běžné období ze simulace ČEZ rozdělené podle cen poslední faktury, v novém cenovém roce podle ceníku produktu. ≈ = položku faktura účtuje za delší období, "
        "do měsíců je rozpočtena (stálé platby podle dnů, spotřeba podle odečtů).</div>`;"
        "return ctl+(chips?`<div style='display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-bottom:8px'>${chips}</div>`:'')"
        "+chart+sbar+hdr+groups+pay+sums+docs+note;"
    )


def prices_sections() -> list[dict]:
    return [
        {
            "type": "grid",
            "column_span": 2,
            "cards": [
                heading("Cenový rozpad", "mdi:cash-multiple"),
                stack(
                    head(
                        PRICE_ENTITY,
                        "mdi:cash-multiple",
                        "Platby podle položek",
                        RJS + "return SP?plab(SP.k)+' · '+(VAT?'s DPH':'bez DPH'):'';",
                        RJS + "return SP?u(f(tot(SP),0),'Kč'):'–';",
                    ),
                    details(prices_body()),
                ),
            ],
        }
    ]


def _tag(section: dict, *requires: str) -> dict:
    return {**section, "_requires": list(requires)} if requires else section


SECTIONS = [
    billing,
    advances,
    *([_tag(contract, "electricity"), _tag(contract_gas, "gas")] if EXPORT else [contract]),
    *([_tag(hdo, "hdo")] if EXPORT else ([hdo] if HDO_ON else [])),
    *grid_sections(),
    *([profile_section()] if G else []),
    *spot_sections(),
    monthly,
    *(
        [_tag(yoy_meter(), "grid"), _tag(yoy, "no_grid", "electricity")]
        if EXPORT
        else [yoy_meter() if G else yoy]
    ),
    totals,
    *([_tag(check, "electricity"), _tag(gas_readings, "gas")] if EXPORT else [check]),
    periods,
    documents,
]
PRICE_SECTIONS = prices_sections()
if not EXPORT:
    SECTIONS = [{k: v for k, v in sec.items() if not k.startswith("_")} for sec in SECTIONS]

view = {
    "title": "ČEZ",
    "path": "cez",
    "icon": "mdi:lightning-bolt-circle",
    "type": "sections",
    "max_columns": 3,
    "sections": SECTIONS,
}
prices_view = {  # own tab of the dashboard (icon in the view bar)
    "title": "Cenový rozpad",
    "path": PRICES_PATH,
    "icon": "mdi:cash-multiple",
    "type": "sections",
    "max_columns": 2,
    "sections": PRICE_SECTIONS,
}

with open(sys.argv[1], "w") as fh:
    json.dump(view, fh, ensure_ascii=False, indent=1)
if len(sys.argv) > 2:  # optional second file: the price breakdown view
    with open(sys.argv[2], "w") as fh:
        json.dump(prices_view, fh, ensure_ascii=False, indent=1)
print("ok")
