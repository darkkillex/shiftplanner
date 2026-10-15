"""
Motore comune del Report commessa.

Le due sorgenti (piani Kairos e file Excel esterno) producono lo stesso
dataset normalizzato tramite `DatasetBuilder`; il front-end lavora solo su
quel dataset e non sa da dove arrivano i dati.

Formato del dataset (JSON):
    source   : {kind: 'kairos'|'excel', label, detail}
    months   : ['2026-01', ...]
    holidays : ['2026-01-01', ...]
    legend   : {codice: {d: descrizione, c: categoria, h: ore}}
    people   : [{n, soc, socFull, mail, tel, presc, liv, eid}]
    mans     : ['Ufficio', ...]                    tabella mansioni (indice)
    rec      : [[p, data, code, cat, ore, m, prep, nota, autore, area, notaPos], ...]
               p = indice in people, m = indice in mans (-1 = nessuna),
               prep = indice in mans della posizione da preposto (-1 = no)
    prep     : [[data, turno, m, riga, p, foglio], ...]   registro preposti
    diag     : [{foglio, esito, mese, giorni, persone, note, esitoNote}]
    orphans  : [{foglio, cella, data, posizione, area, testo, autore}]
    unmatched: ['Cognome Nome', ...]   persone del file non presenti in Kairos
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

# ---------------------------------------------------------------------------
# Legenda codici (foglio MAIN del piano turni ATI)
# ---------------------------------------------------------------------------
CODICI = {
    "A": ("Turno A · 06:00-14:00", "lavoro"),
    "B": ("Turno B · 14:00-22:00", "lavoro"),
    "C": ("Turno C (notte) · 22:00-06:00", "notte"),
    "D": ("Giornaliero · 08:00-17:00", "lavoro"),
    "A1": ("Turno A1 · 07:00-15:00", "lavoro"),
    "B1": ("Turno B1 · 15:00-19:00", "lavoro"),
    "AT": ("Turno AT · 04:00-13:30", "lavoro"),
    "BT": ("Turno BT · 13:30-23:00", "lavoro"),
    "12H-D": ("12 ore giorno · 07:00-19:00", "lavoro"),
    "12H-N": ("12 ore notte · 19:00-07:00", "notte"),
    "F": ("Ferie", "ferie"),
    "P": ("Permesso (PAR)", "ferie"),
    "M": ("Malattia", "assenza"),
    "CON": ("Congedo", "assenza"),
    "CIG": ("Cassa integrazione", "assenza"),
    "SCI": ("Sciopero", "assenza"),
    "PNR": ("Permesso non retribuito", "assenza"),
    "MAT": ("Maternità", "assenza"),
    "PS": ("Permesso sindacale", "assenza"),
    "104": ("Permesso Legge 104", "assenza"),
    "PL": ("Permesso lutto", "assenza"),
    "FOR": ("Formazione", "formazione"),
    "XXX": ("Spare fuori turno", "spare"),
    "CONM": ("Congedo matrimoniale", "assenza"),
    "FNC": ("Fondo nuove competenze", "assenza"),
    "PD": ("Permesso donatore", "assenza"),
    # le formule del piano ATI scrivono "ERROR" quando la cella non è coerente
    # (es. stessa persona su due posizioni): la teniamo visibile come anomalia
    "ERROR": ("Errore nel file (formula Excel)", "anomalia"),
}
# grafie alternative trovate nei file reali
ALIAS = {"FERIE": "F", "PAR": "P", "MALATTIA": "M", "FORMAZIONE": "FOR",
         "12HD": "12H-D", "12HN": "12H-N", "12H D": "12H-D", "12H N": "12H-N"}

# ore convenzionali per codice turno (se la sorgente non fornisce gli orari)
ORE_TURNO = {"A": 8, "B": 8, "C": 8, "D": 8, "A1": 8, "B1": 4, "AT": 9.5, "BT": 9.5,
             "12H-D": 12, "12H-N": 12, "FOR": 8}
NOTTE = {"C", "12H-N"}

# riconoscimento delle righe di assenza dal nome della posizione (piani Kairos)
ROW_KEYWORDS = [
    (r"permesso\s+sindacale", "PS"),
    (r"permesso\s+lutto", "PL"),
    (r"permesso\s+dona", "PD"),
    (r"104", "104"),
    (r"non\s+retribuit", "PNR"),
    (r"congedo\s+matrimonial", "CONM"),
    (r"congedo", "CON"),
    (r"cassa\s+integr", "CIG"),
    (r"sciopero", "SCI"),
    (r"maternit", "MAT"),
    (r"malattia", "M"),
    (r"fondo\s+nuove", "FNC"),
    (r"^ferie", "F"),
    (r"^permess|^par\b", "P"),
    (r"^formazione", "FOR"),
    (r"^spare", "XXX"),
]
_ROW_KW = [(re.compile(p, re.I), c) for p, c in ROW_KEYWORDS]

MESI_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio",
           "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

CATEGORIE = ["lavoro", "notte", "riposo", "ferie", "formazione", "assenza", "spare", "anomalia"]

_SLOT_RE = re.compile(r"^(.*?)(?:\.(\d+))?$")


def split_slot(name: str) -> str:
    """'Ufficio - Preposto.2' -> 'Ufficio - Preposto' (come core.views._split_slot)."""
    m = _SLOT_RE.match((name or "").strip())
    return (m.group(1) or "").strip()


def S(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def norm_code(v) -> str:
    c = S(v).upper()
    return ALIAS.get(c, c)


def code_from_row_name(name: str) -> str:
    for rx, code in _ROW_KW:
        if rx.search(name or ""):
            return code
    return ""


def norm_key(s: str) -> str:
    """Chiave di confronto per i nomi: minuscole, senza accenti né apostrofi."""
    s = unicodedata.normalize("NFD", S(s).lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[’'`]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def short_company(name: str) -> str:
    """'RINA Consulting S.p.a.' -> 'Rina', 'Sivam S.p.a.' -> 'Sivam'."""
    n = S(name)
    low = n.lower()
    if not n:
        return ""
    if "rina" in low:
        return "Rina"
    if "sivam" in low:
        return "Sivam"
    return re.sub(r"\s+s\.?p\.?a\.?$", "", n, flags=re.I).strip()


def is_rest(code: str) -> bool:
    return not code or code in ("-", "0")


class Legend:
    """Legenda codici + ore; le sorgenti possono arricchirla (orari reali)."""

    def __init__(self):
        self.items = {k: {"d": d, "c": c, "h": ORE_TURNO.get(k)} for k, (d, c) in CODICI.items()}

    def set_hours(self, code: str, hours: float | None, label: str | None = None):
        code = norm_code(code)
        if not code:
            return
        it = self.items.setdefault(code, {"d": label or code, "c": "notte" if code in NOTTE else "lavoro", "h": None})
        if hours:
            it["h"] = hours
        if label and it["d"] == code:
            it["d"] = label

    def cat(self, code: str) -> str:
        if is_rest(code):
            return "riposo"
        it = self.items.get(code)
        return it["c"] if it else "lavoro"

    def hours(self, code: str, cat: str) -> float:
        # Ferie/permessi valgono convenzionalmente 8 ore per tutti
        if cat == "ferie":
            return 8
        if cat in ("lavoro", "notte", "formazione"):
            h = (self.items.get(code) or {}).get("h")
            return h if h else 8
        return 0

    def as_json(self):
        return self.items


class DatasetBuilder:
    def __init__(self, kind: str, label: str, detail: str = ""):
        self.source = {"kind": kind, "label": label, "detail": detail}
        self.legend = Legend()
        self.people: list[dict] = []
        self._pidx: dict[str, int] = {}
        self.mans: list[str] = []
        self._midx: dict[str, int] = {}
        self.rec: list[list] = []
        self.prep: list[list] = []
        self.diag: list[dict] = []
        self.orphans: list[dict] = []
        self.unmatched: list[str] = []
        self.months: set[str] = set()

    # -- tabelle -----------------------------------------------------------
    def person(self, name: str, **info) -> int:
        k = norm_key(name)
        if k in self._pidx:
            i = self._pidx[k]
            p = self.people[i]
            for key, v in info.items():
                if v and not p.get(key):
                    p[key] = v
            return i
        p = {"n": S(name), "soc": "", "socFull": "", "mail": "", "tel": "", "presc": "", "liv": "", "eid": None}
        p.update({k2: v for k2, v in info.items() if v is not None})
        self.people.append(p)
        self._pidx[k] = len(self.people) - 1
        return self._pidx[k]

    def mansione(self, m: str) -> int:
        m = S(m)
        if not m:
            return -1
        if m not in self._midx:
            self.mans.append(m)
            self._midx[m] = len(self.mans) - 1
        return self._midx[m]

    # -- record ------------------------------------------------------------
    def add_record(self, p: int, date: dt.date, code: str, mansione: str = "", *,
                   prep_pos: str = "", nota: str = "", autore: str = "", area: str = "", nota_pos: str = ""):
        code = norm_code(code)
        if code in ("-", "0"):
            code = ""
        cat = self.legend.cat(code)
        ore = self.legend.hours(code, cat)
        d = date.isoformat()
        self.months.add(d[:7])
        self.rec.append([p, d, code, cat, ore, self.mansione(mansione),
                         self.mansione(prep_pos) if prep_pos else -1,
                         nota, autore, area, nota_pos])

    def add_prep(self, date: dt.date, turno: str, posizione: str, riga, p: int, foglio: str):
        self.prep.append([date.isoformat(), S(turno), self.mansione(posizione), riga, p, foglio])

    # -- output ------------------------------------------------------------
    def build(self, holidays: list[str]) -> dict:
        self.rec.sort(key=lambda r: (r[0], r[1]))
        self.prep.sort(key=lambda r: (r[0], r[3] if isinstance(r[3], int) else 0))
        return {
            "source": self.source,
            "months": sorted(self.months),
            "holidays": holidays,
            "legend": self.legend.as_json(),
            "people": self.people,
            "mans": self.mans,
            "rec": self.rec,
            "prep": self.prep,
            "diag": self.diag,
            "orphans": self.orphans,
            "unmatched": sorted(set(self.unmatched)),
        }


def shift_hours(start: dt.time | None, end: dt.time | None) -> float | None:
    """Durata di un turno in ore (gestisce lo scavalco della mezzanotte)."""
    if not start or not end:
        return None
    s = start.hour * 60 + start.minute
    e = end.hour * 60 + end.minute
    if s == e:
        return None   # 00:00-00:00: codice senza orario (es. PAR)
    if e < s:
        e += 24 * 60
    return round((e - s) / 60, 2)


class EmployeeNameIndex:
    """
    Abbina un nome "Cognome Nome" (come scritto nel piano turni) ai dipendenti
    di Kairos. Prima il nome completo; se non c'è, una forma tollerante:
    stesso cognome + uno dei nomi ("Pascarelli Pietro" -> "Pascarelli Pietro
    Antonio", "Saponara Michele" -> "Saponara Paolo Michele"), oppure
    "Nome Cognome". La forma tollerante vale solo se il risultato è univoco.
    """

    def __init__(self, employees):
        from collections import defaultdict
        self.exact = defaultdict(list)
        self.loose = defaultdict(list)
        for e in employees:
            last, first = S(e.last_name), S(e.first_name)
            self.exact[norm_key(f"{last} {first}")].append(e)
            self.loose[norm_key(f"{first} {last}")].append(e)
            for tok in first.split():
                self.loose[norm_key(f"{last} {tok}")].append(e)

    def find(self, name: str):
        """-> (dipendente | None, esito) con esito in 'ok', 'ambiguous', 'missing'."""
        k = norm_key(name)
        hits = self.exact.get(k, [])
        if not hits:
            hits = list({e.pk: e for e in self.loose.get(k, [])}.values())
        if len(hits) == 1:
            return hits[0], "ok"
        return None, ("ambiguous" if hits else "missing")
