"""
Import delle prescrizioni mediche dal foglio "Dipendenti" del piano turni ATI
verso Kairos (modello EmployeeMedicalInfo).

Usato sia dal pulsante nel Report commessa (anteprima + applica) sia dal
comando `python manage.py import_prescrizioni <file>`.

Regole:
  - abbinamento per "Cognome Nome" (colonna "Nome su ROTA", altrimenti
    Cognome + Nome), senza differenze di maiuscole, accenti o apostrofi;
    se manca, stesso cognome + uno dei nomi (secondi nomi), solo se univoco;
  - prescrizione nel file e non in Kairos      -> nuova
  - prescrizione diversa da quella in Kairos   -> aggiornata
  - cella vuota nel file ma presente in Kairos -> lasciata com'è, salvo
    clear_missing=True (allora viene rimossa);
  - persone del file non trovate in Kairos, o con omonimi, vengono solo
    segnalate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.db import transaction

from core.models import Employee

from .engine import EmployeeNameIndex
from .models import EmployeeMedicalInfo
from .source_excel import ExcelFormatError, read_dipendenti
from .xlsx_reader import XlsxBook


def _same(a: str, b: str) -> bool:
    return re.sub(r"\s+", " ", a or "").strip() == re.sub(r"\s+", " ", b or "").strip()


@dataclass
class ImportPlan:
    create: list = field(default_factory=list)      # {eid, nome, old, new}
    update: list = field(default_factory=list)
    clear: list = field(default_factory=list)
    unchanged: int = 0
    kept: list = field(default_factory=list)        # vuote nel file, mantenute in Kairos
    not_found: list = field(default_factory=list)   # nomi del file non presenti in Kairos (con prescrizione)
    ambiguous: list = field(default_factory=list)   # omonimi in Kairos
    file_rows: int = 0
    file_with_presc: int = 0

    @property
    def changes(self) -> int:
        return len(self.create) + len(self.update) + len(self.clear)

    def as_dict(self) -> dict:
        return {
            "create": self.create, "update": self.update, "clear": self.clear,
            "unchanged": self.unchanged, "kept": self.kept, "not_found": self.not_found,
            "ambiguous": self.ambiguous, "file_rows": self.file_rows,
            "file_with_presc": self.file_with_presc, "changes": self.changes,
        }


def read_file_prescriptions(fileobj) -> dict:
    """{chiave nome: {"nome", "presc"}} dal foglio Dipendenti."""
    try:
        book = XlsxBook(fileobj)
    except Exception as exc:
        raise ExcelFormatError(f"Il file non è un Excel valido ({exc}).")
    ana = read_dipendenti(book)
    if ana is None:
        raise ExcelFormatError('Foglio "Dipendenti" non trovato nel file.')
    return {k: {"nome": v["nome"], "presc": v["presc"]} for k, v in ana.items()}


def build_plan(file_rows: dict, clear_missing: bool = False) -> ImportPlan:
    plan = ImportPlan(file_rows=len(file_rows))
    index = EmployeeNameIndex(Employee.objects.all())
    current = dict(EmployeeMedicalInfo.objects.values_list("employee_id", "prescriptions"))

    for key, row in sorted(file_rows.items(), key=lambda kv: kv[1]["nome"].lower()):
        new = (row["presc"] or "").strip()
        if new:
            plan.file_with_presc += 1
        e, status = index.find(row["nome"])
        if e is None:
            if new or status == "ambiguous":
                (plan.ambiguous if status == "ambiguous" else plan.not_found).append(row["nome"])
            continue
        old = (current.get(e.id) or "").strip()
        item = {"eid": e.id, "nome": e.full_name(), "old": old, "new": new}
        if new and not old:
            plan.create.append(item)
        elif new and not _same(new, old):
            plan.update.append(item)
        elif not new and old:
            (plan.clear if clear_missing else plan.kept).append(item)
        elif new:
            plan.unchanged += 1
    return plan


@transaction.atomic
def apply_plan(plan: ImportPlan, user=None) -> dict:
    for it in plan.create + plan.update:
        info, _ = EmployeeMedicalInfo.objects.get_or_create(employee_id=it["eid"])
        info.prescriptions = it["new"]
        info.updated_by = user
        info.save()
    if plan.clear:
        EmployeeMedicalInfo.objects.filter(employee_id__in=[it["eid"] for it in plan.clear]).delete()
    return {"create": len(plan.create), "update": len(plan.update), "clear": len(plan.clear)}
