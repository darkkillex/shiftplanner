# core/management/commands/audit_template_plan_integrity.py
import csv
from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import Template, TemplateRow, Plan, PlanRow

class Command(BaseCommand):
    help = "Verifica l'integrità TemplateRow ↔ PlanRow e genera report CSV con eventuali disallineamenti."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=str, default="integrity_audit.csv",
                            help="Percorso file CSV di output (default: integrity_audit.csv)")
        parser.add_argument("--template", type=int, help="Limita ad un template specifico (id)")

    def handle(self, *args, **opts):
        only_tpl = opts.get("template")
        out_path = opts["output"]
        tpls = Template.objects.all()
        if only_tpl:
            tpls = tpls.filter(pk=only_tpl)

        rows = []
        total_plans = 0
        total_issues = 0

        for tpl in tpls:
            tpl_rows = list(TemplateRow.objects.filter(template=tpl).order_by("order"))
            tpl_len = len(tpl_rows)
            plans = Plan.objects.filter(template=tpl)

            for plan in plans:
                total_plans += 1
                plan_rows = list(PlanRow.objects.filter(plan=plan).order_by("order"))
                plan_len = len(plan_rows)

                # Controlla lunghezza
                if tpl_len != plan_len:
                    rows.append({
                        "template_id": tpl.id,
                        "template_name": tpl.name,
                        "plan_id": plan.id,
                        "plan_name": plan.name,
                        "issue": f"Numero righe diverso (template={tpl_len}, plan={plan_len})"
                    })
                    total_issues += 1

                # Confronta ordine per ordine
                for i, tr in enumerate(tpl_rows, start=1):
                    pr = next((p for p in plan_rows if p.order == i), None)
                    if not pr:
                        rows.append({
                            "template_id": tpl.id,
                            "template_name": tpl.name,
                            "plan_id": plan.id,
                            "plan_name": plan.name,
                            "issue": f"Manca PlanRow con order={i} ('{tr.duty}')"
                        })
                        total_issues += 1
                        continue
                    if (tr.duty or "") != (pr.duty or "") or tr.is_spacer != pr.is_spacer:
                        rows.append({
                            "template_id": tpl.id,
                            "template_name": tpl.name,
                            "plan_id": plan.id,
                            "plan_name": plan.name,
                            "issue": f"Mismatch order={i}: template='{tr.duty}', plan='{pr.duty}'"
                        })
                        total_issues += 1

        # Scrittura CSV
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "template_id", "template_name", "plan_id", "plan_name", "issue"
            ])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write("")
        self.stdout.write("=== REPORT INTEGRITÀ ===")
        self.stdout.write(f"Template esaminati: {tpls.count()}")
        self.stdout.write(f"Piani esaminati:    {total_plans}")
        self.stdout.write(f"Anomalie trovate:   {total_issues}")
        self.stdout.write(f"File CSV generato:  {out_path}")
