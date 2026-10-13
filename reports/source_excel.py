"""
Sorgente "file esterno": piano turni ATI in formato Excel (.xlsm/.xlsx).

Struttura attesa di ogni foglio mese (es. "Gennaio 2026"):
  A1 = "Numero mese", B1 = numero del mese
  riga 1/2, da colonna H: le date del mese
  righe 3..812  matrice posizioni x giorni (col. D turno, col. E posizione,
                nelle celle il nome del dipendente; i commenti di cella sono
                le note). Le posizioni con "- Preposto" danno il preposto.
  riga 813      intestazione "DIPENDENTE" (col. E)
  dalla 814     blocco per dipendente, a coppie di righe:
                1a riga = codici turno (A, B, F, M, ...), 2a riga = mansione

Foglio "Dipendenti": Cognome, Nome, Nome su ROTA, Società,
Prescrizioni Mediche, Telefono Mobile, Email Aziendale, Senior/Junior.
Foglio "MAIN": legenda codici con gli orari (col. J codice, col. K orario).

Il file viene solo letto: niente viene scritto nel database di Kairos.
"""
from __future__ import annotations

import datetime as dt
import re

from .engine import MESI_IT as MESI, DatasetBuilder, S, norm_key, short_company, shift_hours, norm_code
from .xlsx_reader import XlsxBook, serial_to_date, cell_ref

MAX_COL = 45          # A..AS: dati del mese + qualche colonna di servizio
FIRST_DAY_COL = 7     # colonna H

_PREP_RX = re.compile(r"preposto", re.I)
_PREP_STRIP = re.compile(r"\s*-\s*Preposto(\s+solo\s+WE)?", re.I)
_TIME_RX = re.compile(r"(\d{1,2})[,.:](\d{2})\s*-\s*(\d{1,2})[,.:](\d{2})")


class ExcelFormatError(Exception):
    pass


def first_line(v) -> str:
    return re.sub(r"\s+", " ", S(v).split("\n")[0]).strip()


def _clean_comment(c: dict | None) -> dict | None:
    if not c:
        return None
    t = re.sub(r"\s*\n+\s*", " ", S(c.get("t")))
    a = S(c.get("a"))
    # Excel a volte antepone "Autore:" al testo
    if a and t.lower().startswith(a.lower() + ":"):
        t = t[len(a) + 1:]
    t = re.sub(r"\s{2,}", " ", t).strip()
    return {"t": t, "a": a} if t else None


def _row(rows, i):
    return rows[i] if 0 <= i < len(rows) else []


def _cell(row, j):
    return row[j] if j < len(row) else None


def _read_anagrafica(book: XlsxBook, b: DatasetBuilder) -> dict:
    """Foglio Dipendenti -> {chiave nome: info}. Colonne cercate per intestazione."""
    sh = next((s for s in book.sheets if s.name.lower() == "dipendenti"), None)
    if not sh:
        b.diag.append({"foglio": "Dipendenti", "esito": "foglio non trovato: società e prescrizioni non disponibili"})
        return {}
    rows = book.read(sh, max_col=30, with_comments=False).rows
    if not rows:
        return {}
    head = [norm_key(h) for h in rows[0]]

    def col(*names):
        for n in names:
            for i, h in enumerate(head):
                if h.startswith(n):
                    return i
        return None

    c_cog, c_nom, c_rota = col("cognome"), col("nome"), col("nome su rota")
    c_soc, c_pre = col("societa", "azienda"), col("prescrizion")
    c_tel, c_mail, c_liv = col("telefono"), col("email", "mail"), col("senior", "livello", "inquadramento")
    out = {}
    for r in rows[1:]:
        cog, nom = S(_cell(r, c_cog)) if c_cog is not None else "", S(_cell(r, c_nom)) if c_nom is not None else ""
        rota = (S(_cell(r, c_rota)) if c_rota is not None else "") or f"{cog} {nom}".strip()
        if not rota:
            continue
        out[norm_key(rota)] = {
            "soc": short_company(_cell(r, c_soc)) if c_soc is not None else "",
            "socFull": S(_cell(r, c_soc)) if c_soc is not None else "",
            "presc": S(_cell(r, c_pre)) if c_pre is not None else "",
            "tel": S(_cell(r, c_tel)) if c_tel is not None else "",
            "mail": S(_cell(r, c_mail)) if c_mail is not None else "",
            "liv": S(_cell(r, c_liv)) if c_liv is not None else "",
        }
    return out


def _read_legend_hours(book: XlsxBook, b: DatasetBuilder):
    """Foglio MAIN: codice in col. J, orario in col. K ('06,00-14,00', '12 ORE')."""
    sh = next((s for s in book.sheets if s.name.upper() == "MAIN"), None)
    if not sh:
        return
    for r in book.read(sh, max_col=12, max_row=80, with_comments=False).rows:
        code, txt = norm_code(_cell(r, 9)), S(_cell(r, 10))
        if not code or not txt or len(code) > 6:
            continue
        m = _TIME_RX.search(txt)
        if m:
            h = shift_hours(dt.time(int(m[1]) % 24, int(m[2])), dt.time(int(m[3]) % 24, int(m[4])))
            b.legend.set_hours(code, h)
        else:
            m2 = re.search(r"(\d+)\s*ORE", txt, re.I)
            if m2:
                b.legend.set_hours(code, float(m2[1]))


def build_from_excel(fileobj, filename: str, kairos_people: dict | None = None) -> dict:
    """
    kairos_people: {chiave nome: {"eid", "soc", "socFull", "mail", "tel"}} per
    abbinare i nomi del file ai dipendenti di Kairos (solo per segnalare chi manca).
    """
    try:
        book = XlsxBook(fileobj)
    except Exception as exc:   # zip corrotto, non è un file Excel, ...
        raise ExcelFormatError(f"Il file non è un Excel valido ({exc}).")

    b = DatasetBuilder("excel", filename, "File esterno: dati letti dal file, nulla viene salvato in Kairos")
    ana = _read_anagrafica(book, b)
    _read_legend_hours(book, b)
    kairos_people = kairos_people or {}

    def person(nome: str, soc_cell: str = "") -> int:
        k = norm_key(nome)
        info = dict(ana.get(k, {}))
        kp = kairos_people.get(k)
        if kp:
            info["eid"] = kp["eid"]
            info.setdefault("mail", kp.get("mail", ""))
        else:
            b.unmatched.append(nome)
        if not info.get("soc"):
            info["soc"] = short_company(soc_cell) or (kp or {}).get("soc", "")
            info["socFull"] = S(soc_cell) or (kp or {}).get("socFull", "")
        return b.person(nome, **info)

    years = set()
    loaded = 0
    ignorati = {}
    for sh in book.sheets:
        if sh.state != "visible":
            if sh.name.lower() not in ("test",):
                b.diag.append({"foglio": sh.name, "esito": "foglio nascosto — ignorato"})
            continue
        # lettura veloce della sola intestazione per capire se è un foglio mese
        head = book.read(sh, max_col=3, max_row=1, with_comments=False).rows
        if not head or S(_cell(head[0], 0)).lower() != "numero mese":
            continue
        try:
            mese = int(float(S(_cell(head[0], 1))))
        except ValueError:
            mese = 0
        if not 1 <= mese <= 12:
            b.diag.append({"foglio": sh.name, "esito": "numero mese non valido in B1"})
            continue

        data = book.read(sh, max_col=MAX_COL)
        rows, comments = data.rows, data.comments

        def commento(r, c):
            return _clean_comment(comments.get((r, c)))

        # colonne giorno: run contiguo di date del mese a partire da H
        r1, r0 = _row(rows, 1), _row(rows, 0)
        date_row = r1 if any(serial_to_date(v) for v in r1[FIRST_DAY_COL:]) else r0
        cols = []
        for j in range(FIRST_DAY_COL, min(len(date_row), MAX_COL)):
            d = serial_to_date(date_row[j])
            if d and d.month == mese:
                cols.append((j, d))
            elif cols:
                break
        if not cols:
            b.diag.append({"foglio": sh.name, "esito": "nessuna colonna data riconosciuta"})
            continue
        years.add(cols[0][1].year)

        hdr = next((i for i, r in enumerate(rows) if S(_cell(r, 4)).upper() == "DIPENDENTE"), -1)
        if hdr < 0:
            b.diag.append({"foglio": sh.name, "esito": "blocco DIPENDENTE non trovato"})
            continue

        # ---- matrice posizioni x giorni: note di cella e preposti ----
        note = {}      # (chiave nome, data) -> {testo, autore, posizione, area, notaPos}
        n_note = 0
        prep_rows = []
        for i in range(2, hdr):
            r = _row(rows, i)
            posiz = S(_cell(r, 4))
            if not posiz or posiz.upper() == "POSIZIONE":
                continue
            area = S(_cell(r, 1))
            npos = commento(i, 1) or commento(i, 4)
            is_prep = bool(_PREP_RX.search(posiz))
            for j, d in cols:
                pers = S(_cell(r, j))
                c = commento(i, j)
                if len(pers) < 3:
                    if c:
                        b.orphans.append({"foglio": sh.name, "cella": cell_ref(i, j), "data": d.isoformat(),
                                          "posizione": posiz, "area": area, "testo": c["t"], "autore": c["a"]})
                    continue
                k = (norm_key(pers), d)
                prev = note.get(k, {})
                if c:
                    n_note += 1
                note[k] = {
                    "testo": " · ".join(x for x in (prev.get("testo"), c["t"] if c else "") if x),
                    "autore": (c or {}).get("a") or prev.get("autore", ""),
                    "posizione": prev.get("posizione") or posiz,
                    "area": prev.get("area") or area,
                    "notaPos": prev.get("notaPos") or (npos or {}).get("t", ""),
                }
                if is_prep:
                    prep_rows.append((d, S(_cell(r, 3)), posiz, i + 1, pers))

        # ---- blocco per dipendente (coppie di righe) ----
        buf = []
        persone = 0
        i = hdr + 1
        while i < len(rows):
            r1 = _row(rows, i)
            nome = S(_cell(r1, 4))
            if len(nome) < 3 or nome.upper() == "DIPENDENTE":
                i += 1
                continue
            r2 = _row(rows, i + 1)
            n2 = S(_cell(r2, 4))
            is_pair = n2 in ("", nome)
            mans_row = r2 if is_pair else []
            persone += 1
            soc = S(_cell(r1, 5))
            if len(soc) > 12 or soc.lower() in ("turno", "mansione"):
                soc = ""
            for j, d in cols:
                code = S(_cell(r1, j)).upper()
                mans = first_line(_cell(mans_row, j))
                if mans in ("-", "0"):
                    mans = ""
                mans = re.sub(r"\s*-\s*$", "", mans)
                mans = re.sub(r"\s{2,}", " ", mans).strip()
                nt = note.get((norm_key(nome), d), {})
                buf.append((nome, soc, d, code, mans or nt.get("posizione", ""), nt))
            i += 2 if is_pair else 1

        pieni = sum(1 for x in buf if x[4] or (x[3] and x[3] not in ("-", "0")))
        if not pieni:
            b.diag.append({"foglio": sh.name, "esito": "piano vuoto — non caricato", "mese": MESI[mese - 1],
                           "giorni": len(cols), "persone": persone, "note": n_note})
            continue

        # nomi validi: blocco dipendenti + foglio Dipendenti. Altri testi nelle
        # celle della matrice (es. "Assenza") sono segnaposto, non persone.
        known = {norm_key(x[0]) for x in buf} | set(ana)
        prep_map = {}
        for d, turno, posiz, riga, pers in prep_rows:
            if norm_key(pers) not in known:
                ignorati[pers] = ignorati.get(pers, 0) + 1
                continue
            p = person(pers)
            b.add_prep(d, turno, posiz, riga, p, sh.name)
            prep_map[(norm_key(pers), d)] = posiz

        abbinate = 0
        for nome, soc, d, code, mans, nt in buf:
            p = person(nome, soc)
            if mans.upper() == "ERROR":
                mans = ""
            if nt.get("testo"):
                abbinate += 1
            b.add_record(p, d, code, mans,
                         prep_pos=prep_map.get((norm_key(nome), d), ""),
                         nota=nt.get("testo", ""), autore=nt.get("autore", ""),
                         area=nt.get("area", ""), nota_pos=nt.get("notaPos", ""))
        loaded += 1
        b.diag.append({"foglio": sh.name, "esito": "caricato", "mese": MESI[mese - 1], "giorni": len(cols),
                       "persone": persone, "note": n_note,
                       "esitoNote": f"{abbinate}/{n_note} note abbinate a un dipendente" if n_note else "nessuna nota"})

    if ignorati:
        b.diag.append({"foglio": "(tutti)", "esito": "valori nelle posizioni da preposto non riconosciuti come "
                       "dipendenti, ignorati: " + ", ".join(f"«{k}» ×{v}" for k, v in sorted(ignorati.items()))})
    if not loaded:
        raise ExcelFormatError('Nessun foglio mese riconosciuto. Serve un foglio con "Numero mese" in A1 '
                               'e la riga "DIPENDENTE" in colonna E.')
    from core.views import italy_holidays
    hol = sorted(d.isoformat() for y in years for d in italy_holidays(y))
    return b.build(hol)
