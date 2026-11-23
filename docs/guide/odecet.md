# Odečet elektroměru

Vnitřní záložka **Odečet** (ikona počítadla) u odběrného místa slouží k zadání samoodečtu
elektroměru nebo plynoměru přímo z Home Assistantu, stejně jako na portálu Můj ČEZ. Hodnoty se
kontrolují už při psaní podle stejných pravidel jako na portálu, takže se včas ukáže
překlep nebo přehozená čísla.

Kartu dodává integrace sama, není potřeba nic doinstalovat. Na vlastní dashboard ji
lze přidat jako kartu typu `custom:muj-cez-reading-card` (volitelně `entry_id` pro
konkrétní účet, `ean` jen pro jedno odběrné místo a `title`). Ikona **?** v záhlaví karty
otevře tuto stránku.

## Formulář

![Formulář odečtu](img/odecet-formular.png)

1. **Odběrné místo**: odběrná místa elektřiny účtu. Při více místech se vybírá ze
   seznamu, u jednoho je jen zobrazené.
2. **Typ odečtu**: nabízí jen typy, které portál u místa právě povoluje. Pod výběrem je
   popis, co se s odečtem stane:
   - *Kontrolní odečet pro distributora*: předá se distributorovi a zohlední ve
     vyúčtování (počet za rok je omezený, karta ukáže, kolik zbývá).
   - *Deníčkový odečet*: jen pro vaše sledování, distributorovi se nepředává.
   - *Odečet pro mimořádné vyúčtování*: předá se distributorovi a vystaví se podle něj
     mimořádné vyúčtování.
   - *Odečet pro informace o vyúčtování*: přehled o spotřebě, předává se distributorovi.
3. **Stav ke dni**: výchozí je dnešek. Portál přijme jen datum v určitém rozsahu
   (většinou 30 dní zpět, u mimořádného vyúčtování méně) a ne dřív než poslední odečet.
4. **Číslo elektroměru**: doplní se samo podle odečtů z portálu.
5. **Poslední stav**: poslední známý odečet z portálu (distributor i vaše samoodečty),
   načtený čerstvě při otevření záložky.
6. **Vysoký tarif (T1)**: stav v celých kWh, číslice před desetinnou čárkou.
7. **Nízký tarif (T2)**: jen u dvoutarifové sazby.
8. **Poznámka pro vás**: volitelný text do 160 znaků, uloží se k odečtu na portálu.
9. **Zkontrolovat a odeslat**: aktivní, jakmile jsou hodnoty v pořádku.
10. **?**: otevře tuto stránku příručky.

## Kontrola hodnot

![Chyba a varování při zadání](img/odecet-kontrola.png)

- **Červeně (chyba)**: hodnota nižší než předchozí stav, chybějící nebo neceločíselná
  hodnota, datum mimo povolený rozsah, druhý odečet stejného typu v jednom dni nebo
  vyčerpané kontrolní odečty. Odeslat nejde.
- **Oranžově (varování)**: hodnota je nezvykle vysoká, tj. spotřeba od posledního stavu
  přesahuje 1,5× obvyklou denní spotřebu za poslední zúčtovací období. Odeslat lze,
  jde jen o upozornění na možný překlep.
- Pod každou hodnotou je spotřeba od posledního stavu a průměr na den.

## Souhrn a odeslání

![Souhrn před odesláním](img/odecet-souhrn.png)

Po kliknutí na **Zkontrolovat a odeslat** se zobrazí souhrn se spotřebou od posledního
stavu. Teprve **Odeslat odečet** pošle odečet na portál, **Zpět** vrátí formulář.
U typů, které se předávají distributorovi, je v souhrnu upozornění.

Po odeslání karta potvrdí výsledek a načte nový poslední stav. Portál odečet zařadí mezi
odečty elektroměru až po několika minutách, integrace proto na pozadí po 1, 5, 15 a 30
minutách znovu načte odečty, simulaci vyúčtování a zálohy tohoto odběrného místa. Jakmile
se nový odečet objeví, další kontroly se přeskočí. Senzory (stav elektroměru VT a NT,
predikce vyúčtování) se aktualizují bez restartu. Pokud portál hodnoty
označí jako neobvyklé nebo je distributor zamítne, karta to oznámí; zamítnutý odečet
je potřeba zadat znovu na portálu s fotografií displeje.

Odeslat odečet mohou jen administrátoři Home Assistantu.

## Plyn

U plynového odběrného místa karta nabízí **Stav plynoměru** v celých m³ (číslice před
desetinnou čárkou na počítadle) a typy odečtu, které portál pro plyn povolí. Obvyklá
spotřeba pro upozornění „nezvykle vysoká“ se počítá z odečtů za poslední zúčtovací rok,
protože portál ji u plynu neuvádí; v topné sezóně se proto upozornění může objevit i
u správné hodnoty, odeslání nebrání.
