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
    "const dt=(v)=>v?String(v).slice(0,10).split('-').reverse().join('.'):'–';"
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
                "+row('stav_elektromeru','Stav elektroměru',num('stav_elektromeru')+' kWh · '+dt(at('stav_elektromeru','reading_date')))"
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
                "Predikce podle HA",
                "mdi:chart-bar",
                "const p=(CA.periods||[]).find(x=>x.predicted);"
                "const v=p?(val(p,'ha')??val(p,'cez')):null;return u(f(v),UL);",
            ),
            cdetails(
                "const ms=CA.months||[];const c=CA.current||{};"
                "const g=ms.map((m,i)=>({l:m.month.endsWith('-01')?mlab(m.month):MN[+m.month.slice(5)-1],b:["
                "{v:val(m,'cez'),c:CZ,n:'ČEZ'+(m.estimated?' (odhad)':''),o:{hatch:m.estimated}},"
                "{v:val(m,'ha'),c:HA,n:'HA'+(m.ha_partial?' (zatím)':''),o:{dim:m.ha_partial}}],h:mlab(m.month)+' ('+dt(m.from).slice(0,6)+'–'+dt(m.to).slice(0,6)+')',"
                "x:(m.ha_kwh!=null&&m.cez_kwh)?['HA vs ČEZ '+pct((m.ha_kwh-m.cez_kwh)/m.cez_kwh*100)]:[]}));"
                "return chart(g,[[CZ,'ČEZ – rozpis odečtů'],[CZ,'ČEZ – odhad do konce období',{hatch:1}],"
                "[HA,'HA naměřeno'],[HA,'HA – běžící měsíc',{dim:1}]])"
                "+row('odchylka_od_cez','ČEZ do posledního odečtu ('+dt(c.measured_until)+')',f(c.cez_measured_kwh)+' kWh')"
                "+row('odchylka_od_cez','HA za stejné období',f(c.ha_measured_kwh,1)+' kWh')"
                "+row('odchylka_od_cez','Odchylka HA od ČEZ',pct(c.diff_pct));",
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
                "Odchylka HA/ČEZ",
                "mdi:chart-box-outline",
                "const p=(CA.periods||[]).filter(x=>!x.predicted&&x.diff_pct!=null).pop();"
                "return p?u(pct(p.diff_pct).replace(' %',''),'% · '+p.label):'–';",
            ),
            cdetails(
                "const ps=CA.periods||[];"
                "const g=ps.map(p=>{const ok=p.ha_coverage==='full';return {l:p.label,s:p.diff_pct!=null?pct(p.diff_pct):'',"
                "h:'Období '+p.label+' ('+dt(p.from)+' – '+dt(p.to)+')',x:p.diff_pct!=null?['HA vs ČEZ '+pct(p.diff_pct)]:(p.ha_coverage==='partial'?['HA data jen za část období']:[]),"
                "b:[{v:val(p,'cez'),c:CZ,n:'ČEZ'+(p.predicted?' (predikce)':''),o:{hatch:p.predicted}},"
                "{v:ok?val(p,'ha'):null,c:HA,n:'HA'+(p.predicted?' (naměřeno + odhad)':''),"
                "o:{hatch:p.predicted}}]}});"
                "return chart(g,[[CZ,'ČEZ fakturováno'],[HA,'HA naměřeno'],[CZ,'predikce',{hatch:1}]],130)"
                "+`<div style='font-size:12px;color:var(--secondary-text-color);padding:4px 0;white-space:normal'>HA data od "
                "${dt(CA.ha_first_day)}; období bez úplných dat HA jsou jen za ČEZ.</div>`;",
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


def _tag(section: dict, *requires: str) -> dict:
    return {**section, "_requires": list(requires)} if requires else section


SECTIONS = [
    billing,
    advances,
    contract,
    *([_tag(hdo, "hdo")] if EXPORT else ([hdo] if HDO_ON else [])),
    *grid_sections(),
    *spot_sections(),
    monthly,
    *([_tag(yoy_meter(), "grid"), _tag(yoy, "no_grid")] if EXPORT else [yoy_meter() if G else yoy]),
    totals,
    check,
    periods,
    documents,
]
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

with open(sys.argv[1], "w") as fh:
    json.dump(view, fh, ensure_ascii=False, indent=1)
print("ok")
