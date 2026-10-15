"""
Import di un mese del piano turni ATI (.xlsm) in Kairos: Template + Plan + Assignment.

Per ogni foglio mese richiesto:
  1. Template "<prefisso> <Mese Anno>" ricavato dalla matrice posizioni x giorni
     (righe 3..812): una TemplateRow per ogni posizione (colonna E) con il turno
     di riga (colonna D) e l'area/POS (colonna B) nelle note; le righe vuote
     diventano separatori (più righe vuote consecutive = un solo separatore).
  2. Plan del mese creato dal template con la stessa logica di "Crea piano"
     (core.views.plan_create): PlanRow con slot "Posizione.N" e Profession.
  3. Assignment per ogni cella con un nome: dipendente abbinato per
     "Cognome Nome" (EmployeeNameIndex), turno = turno della riga (come nella
     griglia), nota = commento della cella.

Nomi non riconosciuti (es. "Assenza", persone non in anagrafica) e commenti
su celle vuote vengono saltati e segnalati. Tipi turno mancanti in Kairos
(es. PD) vengono creati con la descrizione e gli orari del foglio MAIN.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from core.models import Assignment, Employee, Plan, PlanRow, Profession, ShiftType, Template, TemplateRow

from .engine import CODICI, MESI_IT, EmployeeNameIndex, S, norm_code
from .source_excel import ExcelFormatError, _clean_comment
from .xlsx_reader import XlsxBook, cell_ref, serial_to_date

FIRST_DAY_COL = 7          # H
MAX_COL = 45
NOTE_MAX = 255             # Assignment.notes
ROW_NOTE_MAX = 200         # TemplateRow/PlanRow.notes
_TIME_RX = re.compile(r"(\d{1,2})[,.:](\d{2})\s*-\s*(\d{1,2})[,.:](\d{2})")


@dataclass
class MonthPlan:
    sheet: str
    year: int
    month: int
    template_name: str
    plan_name: str
    rows: list = field(default_factory=list)          # [{"spacer": bool, "duty", "shift", "notes", "cells": {date: (nome, nota)}}]
    assignments: int = 0
    notes: int = 0
    truncated_notes: int = 0
    unmatched: Counter = field(default_factory=Counter)      # nome -> celle
    ambiguous: Counter = field(default_factory=Counter)
    orphans: list = field(default_factory=list)              # commenti su celle senza nome
    double_booked: int = 0                                    # stessa persona su più righe nello stesso giorno
    plan_exists: bool = False
    template_exists: bool = False

    @property
    def positions(self):
        return sum(1 for r in self.rows if not r["spacer"])

    @property
    def spacers(self):
        return sum(1 for r in self.rows if r["spacer"])


@dataclass
class ImportPlan:
    months: list = field(default_factory=list)
    new_shift_types: dict = field(default_factory=dict)       # code -> (label, start, end)


def _legend(book: XlsxBook) -> dict:
    """MAIN: codice (col. J) -> (descrizione, inizio, fine)."""
    sh = next((s for s in book.sheets if s.name.upper() == "MAIN"), None)
    out = {}
    if not sh:
        return out
    for r in book.read(sh, max_col=12, max_row=80, with_comments=False).rows:
        code = norm_code(r[9] if len(r) > 9 else None)
        txt = S(r[10]) if len(r) > 10 else ""
        if not code or len(code) > 6 or code == "SPARE":
            continue
        m = _TIME_RX.search(txt)
        if m:
            start, end = dt.time(int(m[1]) % 24, int(m[2])), dt.time(int(m[3]) % 24, int(m[4]))
            label = f"Turno {code}"
        else:
            start = end = dt.time(0, 0)
            label = txt or (CODICI.get(code, (code,))[0])
        out[code] = (label[:60], start, end)
    return out


def _month_sheet(book: XlsxBook, month: int, year: int):
    for sh in book.sheets:
        if sh.state != "visible":
            continue
        head = book.read(sh, max_col=3, max_row=2, with_comments=False).rows
        if not head or S(head[0][0] if head[0] else "").lower() != "numero mese":
            continue
        try:
            if int(float(S(head[0][1]))) != month:
                continue
        except (ValueError, IndexError):
            continue
        if str(year) in sh.name or len(head) < 2:
            return sh
        d = serial_to_date(head[1][FIRST_DAY_COL] if len(head[1]) > FIRST_DAY_COL else None)
        if d and d.year == year:
            return sh
    return None


def build_import(fileobj, months: list[tuple[int, int]], template_prefix: str = "Template ATI") -> ImportPlan:
    try:
        book = XlsxBook(fileobj)
    except Exception as exc:
        raise ExcelFormatError(f"Il file non è un Excel valido ({exc}).")
    legend = _legend(book)
    index = EmployeeNameIndex(Employee.objects.all())
    existing_codes = set(ShiftType.objects.values_list("code", flat=True))
    out = ImportPlan()

    for year, month in months:
        sh = _month_sheet(book, month, year)
        if sh is None:
            raise ExcelFormatError(f"Foglio di {MESI_IT[month - 1]} {year} non trovato nel file.")
        data = book.read(sh, max_col=MAX_COL)
        rows, comments = data.rows, data.comments

        # colonne giorno: run contiguo di date del mese da H (la colonna AP con
        # il primo del mese è una cella di servizio e resta esclusa)
        date_row = rows[1] if len(rows) > 1 else []
        cols = []
        for j in range(FIRST_DAY_COL, min(len(date_row), MAX_COL)):
            d = serial_to_date(date_row[j])
            if d and d.month == month and d.year == year:
                cols.append((j, d))
            elif cols:
                break
        if not cols:
            raise ExcelFormatError(f"{sh.name}: nessuna colonna data riconosciuta.")
        hdr = next((i for i, r in enumerate(rows) if len(r) > 4 and S(r[4]).upper() == "DIPENDENTE"), None)
        if hdr is None:
            raise ExcelFormatError(f"{sh.name}: riga DIPENDENTE non trovata.")

        label = f"{MESI_IT[month - 1]} {year}"
        mp = MonthPlan(sheet=sh.name, year=year, month=month,
                       template_name=f"{template_prefix} {label}", plan_name=label)
        mp.plan_exists = Plan.objects.filter(year=year, month=month).exists()
        mp.template_exists = Template.objects.filter(name=mp.template_name).exists()

        per_person_day = Counter()
        for i in range(2, hdr):
            r = rows[i] if i < len(rows) else []
            get = lambda j: (r[j] if j < len(r) else None)
            pos = re.sub(r"\s+", " ", S(get(4)))
            if pos.upper() == "POSIZIONE":
                continue
            if not pos:
                if mp.rows and not mp.rows[-1]["spacer"]:
                    mp.rows.append({"spacer": True})
                continue
            code = norm_code(get(3)) or norm_code(get(2))
            if code and code not in existing_codes and code not in out.new_shift_types:
                out.new_shift_types[code] = legend.get(code) or (CODICI.get(code, (code,))[0][:60], dt.time(0), dt.time(0))
            row = {"spacer": False, "duty": pos, "shift": code, "notes": S(get(1))[:ROW_NOTE_MAX],
                   "excel_row": i + 1, "cells": {}}
            for j, d in cols:
                nome = re.sub(r"\s+", " ", S(get(j)))
                c = _clean_comment(comments.get((i, j)))
                if len(nome) < 3:
                    if c:
                        mp.orphans.append({"cella": cell_ref(i, j), "data": d.isoformat(), "posizione": pos, "testo": c["t"]})
                    continue
                emp, status = index.find(nome)
                if emp is None:
                    (mp.ambiguous if status == "ambiguous" else mp.unmatched)[nome] += 1
                    continue
                nota = c["t"] if c else ""
                if len(nota) > NOTE_MAX:
                    nota = nota[:NOTE_MAX - 1] + "…"
                    mp.truncated_notes += 1
                row["cells"][d] = (emp.id, nota)
                mp.assignments += 1
                mp.notes += bool(nota)
                per_person_day[(emp.id, d)] += 1
            mp.rows.append(row)
        while mp.rows and mp.rows[-1]["spacer"]:
            mp.rows.pop()
        mp.double_booked = sum(1 for v in per_person_day.values() if v > 1)
        out.months.append(mp)
    return out


@transaction.atomic
def apply_import(plan: ImportPlan, user, replace: bool = False) -> list[dict]:
    shifts = {s.code: s for s in ShiftType.objects.all()}
    for code, (label, start, end) in plan.new_shift_types.items():
        if code not in shifts:
            shifts[code] = ShiftType.objects.create(code=code, label=label, start_time=start, end_time=end)

    results = []
    for mp in plan.months:
        if mp.plan_exists or mp.template_exists:
            if not replace:
                results.append({"mese": mp.plan_name, "esito": "saltato: piano o template già presenti (usa --replace)"})
                continue
            Plan.objects.filter(year=mp.year, month=mp.month).delete()
            Template.objects.filter(name=mp.template_name, plans__isnull=True).delete()
            if Template.objects.filter(name=mp.template_name).exists():
                results.append({"mese": mp.plan_name, "esito": f"saltato: il template «{mp.template_name}» "
                                "è usato da altri piani"})
                continue

        # 1) template: duty senza suffisso, come "Crea template"
        template = Template.objects.create(name=mp.template_name, is_active=True)
        trows, order = [], 0
        for r in mp.rows:
            order += 1
            if r["spacer"]:
                trows.append(TemplateRow(template=template, order=order, duty="", is_spacer=True))
            else:
                trows.append(TemplateRow(template=template, order=order, duty=r["duty"], is_spacer=False,
                                         notes=r["notes"], shift_type=shifts.get(r["shift"])))
        TemplateRow.objects.bulk_create(trows)

        # 2) piano dal template, stessa numerazione slot di core.views.plan_create
        p = Plan.objects.create(month=mp.month, year=mp.year, name=mp.plan_name, status="Draft",
                                created_by=user, template=template)
        occ = defaultdict(int)
        prow_objs, cell_targets = [], []
        prof_cache = {}
        for tr, r in zip(trows, mp.rows):
            if tr.is_spacer:
                prow_objs.append(PlanRow(plan=p, order=tr.order, duty="", is_spacer=True, notes=tr.notes))
                continue
            occ[tr.duty] += 1
            duty_full = f"{tr.duty}.{occ[tr.duty]}"
            if duty_full not in prof_cache:
                prof_cache[duty_full], _ = Profession.objects.get_or_create(name=duty_full)
            prow_objs.append(PlanRow(plan=p, order=tr.order, duty=duty_full, is_spacer=False,
                                     notes=tr.notes, shift_type=tr.shift_type))
            for d, (eid, nota) in r["cells"].items():
                cell_targets.append(Assignment(plan=p, profession=prof_cache[duty_full], date=d, employee_id=eid,
                                               shift_type=tr.shift_type, notes=nota))
        PlanRow.objects.bulk_create(prow_objs)
        Assignment.objects.bulk_create(cell_targets, batch_size=1000)
        results.append({"mese": mp.plan_name, "esito": "creato", "plan_id": p.id, "template_id": template.id,
                        "righe": len(prow_objs), "assegnazioni": len(cell_targets)})
    return results
