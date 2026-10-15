"""
Sorgente predefinita: piani turni gestiti in Kairos.

Mappatura sul modello del piano turni ATI:
  PlanRow (riga del piano)  = posizione       (nome senza suffisso ".N")
  Assignment                = nome in cella   (dipendente, data, turno, nota)
  riga con "Preposto"       = preposto del giorno
  righe Ferie/Malattia/...  = giustificativi  (codice dal turno o dal nome riga)
  giorno senza assegnazione = riposo
"""
from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict

from core.models import Assignment, Employee, Plan, PlanRow, ShiftType

from .engine import (DatasetBuilder, EmployeeNameIndex, MESI_IT, S, code_from_row_name, norm_code, norm_key,
                     shift_hours, short_company, split_slot)
from .models import EmployeeMedicalInfo

PRIORITA = {"lavoro": 0, "notte": 0, "formazione": 1, "spare": 2, "ferie": 3, "assenza": 3, "riposo": 9}


class KairosPeople:
    """Dipendenti Kairos per abbinare i nomi del file Excel: .get(nome) -> info | None."""

    def __init__(self):
        self.index = EmployeeNameIndex(Employee.objects.select_related("company"))

    def get(self, name, default=None):
        e, status = self.index.find(name)
        if e is None:
            return default
        return {
            "eid": e.id,
            "soc": short_company(e.company.name if e.company else ""),
            "socFull": e.company.name if e.company else "",
            "mail": e.email or "",
            "tel": e.phone or "",
        }


def kairos_people_index() -> KairosPeople:
    return KairosPeople()


def available_years() -> list[int]:
    return sorted(set(Plan.objects.values_list("year", flat=True)), reverse=True)


def plans_for(year: int, month_from: int = 1, month_to: int = 12):
    return list(Plan.objects.filter(year=year, month__gte=month_from, month__lte=month_to)
                .order_by("month"))


def build_from_kairos(year: int, month_from: int = 1, month_to: int = 12) -> dict:
    plans = plans_for(year, month_from, month_to)
    if month_from == 1 and month_to == 12:
        label = f"Piani Kairos {year}"
    elif month_from == month_to:
        label = f"Piano Kairos {MESI_IT[month_from - 1]} {year}"
    else:
        label = f"Piani Kairos {MESI_IT[month_from - 1]}–{MESI_IT[month_to - 1]} {year}"
    b = DatasetBuilder("kairos", label, f"{len(plans)} piano/i letti dal database di Kairos")

    # orari reali dei turni definiti in Kairos
    for st in ShiftType.objects.all():
        b.legend.set_hours(st.code, shift_hours(st.start_time, st.end_time), st.label)

    if not plans:
        from core.views import italy_holidays
        return b.build(sorted(d.isoformat() for d in italy_holidays(year)))

    # prescrizioni (modello separato, solo per questo modulo)
    presc = dict(EmployeeMedicalInfo.objects.values_list("employee_id", "prescriptions"))

    for plan in plans:
        ndays = calendar.monthrange(plan.year, plan.month)[1]
        mese_label = f"{MESI_IT[plan.month - 1]} {plan.year}"

        rows = list(PlanRow.objects.filter(plan=plan, is_spacer=False)
                    .select_related("shift_type").order_by("order"))
        # nome completo della riga ("Ufficio - Preposto.2") -> info riga
        row_by_duty = {}
        for r in rows:
            full = S(r.duty)
            if full:
                row_by_duty[full] = r

        ass = (Assignment.objects.filter(plan=plan)
               .select_related("employee", "employee__company", "profession", "shift_type"))

        per_day = defaultdict(list)     # (employee_id, date) -> [(ordine, info)]
        employees = {}
        n_note = 0
        for a in ass:
            full = S(a.profession.name) if a.profession_id else ""
            row = row_by_duty.get(full)
            base = split_slot(full)
            order = row.order if row else 10 ** 6
            row_code = norm_code(row.shift_type.code) if row and row.shift_type else ""
            code = norm_code(a.shift_type.code) if a.shift_type else row_code
            kw = code_from_row_name(base)
            # una riga "Ferie", "Malattia", ... vale come giustificativo anche se
            # il turno associato è un turno di lavoro o manca del tutto
            if kw and b.legend.cat(code) in ("lavoro", "notte", "riposo"):
                code = kw
            if a.notes:
                n_note += 1
            per_day[(a.employee_id, a.date)].append((order, {
                "code": code, "base": base, "turno": row_code or code,
                "prep": "preposto" in base.lower(), "nota": S(a.notes),
            }))
            employees[a.employee_id] = a.employee

        pidx = {}
        for eid, e in employees.items():
            pidx[eid] = b.person(
                e.full_name(), eid=eid,
                soc=short_company(e.company.name if e.company else ""),
                socFull=e.company.name if e.company else "",
                mail=e.email or "", tel=e.phone or "", presc=presc.get(eid, ""),
            )

        for (eid, day), items in per_day.items():
            items.sort(key=lambda x: (PRIORITA.get(b.legend.cat(x[1]["code"]), 5), x[0]))
            main = items[0][1]
            prep_item = next((it for _, it in sorted(items, key=lambda x: x[0]) if it["prep"]), None)
            nota = " · ".join(it["nota"] for _, it in sorted(items, key=lambda x: x[0]) if it["nota"])
            b.add_record(pidx[eid], day, main["code"], main["base"],
                         prep_pos=prep_item["base"] if prep_item else "", nota=nota)
            for order, it in items:
                if it["prep"]:
                    b.add_prep(day, it["turno"], it["base"], order, pidx[eid], mese_label)

        # giorni senza assegnazione = riposo, per chi compare nel piano
        for eid in employees:
            for d in range(1, ndays + 1):
                day = dt.date(plan.year, plan.month, d)
                if (eid, day) not in per_day:
                    b.add_record(pidx[eid], day, "")

        b.diag.append({"foglio": plan.name or mese_label, "esito": "caricato", "mese": MESI_IT[plan.month - 1],
                       "giorni": ndays, "persone": len(employees), "note": n_note,
                       "esitoNote": f"stato: {plan.status} · revisione {plan.revision}"})

    from core.views import italy_holidays
    hol = sorted(d.isoformat() for y in {p.year for p in plans} for d in italy_holidays(y))
    return b.build(hol)
