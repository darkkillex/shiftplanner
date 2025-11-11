# core/management/commands/sync_template_plan_rows.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from core.models import Template, TemplateRow, Plan, PlanRow, Assignment

def _normalize_plan_orders(plan: Plan):
    rows = list(PlanRow.objects.filter(plan=plan).order_by('order', 'id'))
    for i, r in enumerate(rows, start=1):
        if r.order != i:
            r.order = i
            r.save(update_fields=['order'])

def _normalize_template_orders(template: Template):
    rows = list(TemplateRow.objects.filter(template=template).order_by('order', 'id'))
    for i, r in enumerate(rows, start=1):
        if r.order != i:
            r.order = i
            r.save(update_fields=['order'])

class Command(BaseCommand):
    help = (
        "Audit e fix tra TemplateRow e PlanRow per 'order'. "
        "Default: dry-run. Usa --apply per applicare."
    )

    def add_arguments(self, parser):
        parser.add_argument("--template", type=int, help="ID Template da limitare")
        parser.add_argument("--apply", action="store_true", help="Applica le modifiche")
        parser.add_argument("--verbose", action="store_true", help="Log dettagliato")

    def handle(self, *args, **opts):
        only_tpl_id = opts.get("template")
        do_apply = opts.get("apply", False)
        verbose = opts.get("verbose", False)

        tpls = Template.objects.all()
        if only_tpl_id:
            tpls = tpls.filter(pk=only_tpl_id)

        total_plans = 0
        fixes_inserted = 0
        fixes_deleted = 0
        fixes_updated = 0
        blocked_changes = 0

        for tpl in tpls:
            _normalize_template_orders(tpl)
            desired = list(TemplateRow.objects.filter(template=tpl).order_by("order"))
            desired_len = len(desired)

            plans = Plan.objects.filter(template=tpl)
            for plan in plans:
                total_plans += 1
                _normalize_plan_orders(plan)
                current = list(PlanRow.objects.filter(plan=plan).order_by("order"))
                cur_len = len(current)

                # 1) Inserisci righe mancanti per completare la stessa lunghezza del template
                if cur_len < desired_len:
                    missing_n = desired_len - cur_len
                    if verbose:
                        self.stdout.write(f"[{plan.id}] +{missing_n} righe mancanti (aggiungo in coda)")
                    if do_apply:
                        with transaction.atomic():
                            start_order = cur_len + 1
                            to_create = []
                            for idx in range(start_order, desired_len + 1):
                                tr = desired[idx - 1]
                                to_create.append(PlanRow(
                                    plan=plan,
                                    order=idx,
                                    duty=(tr.duty or ""),
                                    is_spacer=tr.is_spacer,
                                    notes=tr.notes,
                                ))
                            PlanRow.objects.bulk_create(to_create)
                            _normalize_plan_orders(plan)
                    fixes_inserted += (desired_len - cur_len)

                # 2) Se ci sono righe in eccesso rispetto al template, tenta rimozione solo se vuote e senza assegnazioni
                elif cur_len > desired_len:
                    excess_orders = list(range(desired_len + 1, cur_len + 1))
                    if verbose:
                        self.stdout.write(f"[{plan.id}] -{len(excess_orders)} righe in eccesso")
                    for ord_ in reversed(excess_orders):
                        pr = PlanRow.objects.filter(plan=plan, order=ord_).first()
                        if not pr:
                            continue
                        duty = (pr.duty or "").strip()
                        has_ass = Assignment.objects.filter(plan=plan, profession__name=duty).exists() if duty else False
                        if has_ass:
                            blocked_changes += 1
                            if verbose:
                                self.stdout.write(f"  [skip] order={ord_} '{duty}' ha assegnazioni")
                            continue
                        if do_apply:
                            pr.delete()
                        fixes_deleted += 1
                    if do_apply:
                        _normalize_plan_orders(plan)

                # 3) Allinea attributi per ogni posizione (senza toccare righe con assegnazioni)
                #    - Se mismatch is_spacer/duty e NON ci sono assegnazioni, aggiorna per aderire al template
                current = list(PlanRow.objects.filter(plan=plan).order_by("order"))
                for i in range(min(len(current), desired_len)):
                    pr = current[i]
                    tr = desired[i]
                    need_update = False

                    target_is_spacer = bool(tr.is_spacer)
                    target_duty = (tr.duty or "")

                    if pr.is_spacer != target_is_spacer or (pr.duty or "") != target_duty:
                        # verifica assegnazioni su duty attuale
                        duty_now = (pr.duty or "").strip()
                        has_ass = Assignment.objects.filter(plan=plan, profession__name=duty_now).exists() if duty_now else False
                        if has_ass:
                            blocked_changes += 1
                            if verbose:
                                self.stdout.write(f"  [diff] order={pr.order}: '{duty_now}' vs '{target_duty}' (assegnazioni presenti, non modifico)")
                        else:
                            need_update = True

                    if need_update and do_apply:
                        pr.is_spacer = target_is_spacer
                        pr.duty = target_duty
                        pr.notes = tr.notes
                        pr.save(update_fields=["is_spacer", "duty", "notes"])
                        fixes_updated += 1

                if do_apply:
                    _normalize_plan_orders(plan)

        # Report finale
        self.stdout.write("")
        self.stdout.write("=== SYNC REPORT ===")
        self.stdout.write(f"Piani esaminati: {total_plans}")
        self.stdout.write(f"Righe create:    {fixes_inserted}")
        self.stdout.write(f"Righe eliminate: {fixes_deleted}")
        self.stdout.write(f"Righe aggiornate:{fixes_updated}")
        self.stdout.write(f"Bloccate (assegn.): {blocked_changes}")
        self.stdout.write(f"Modalità: {'APPLY' if do_apply else 'DRY-RUN'}")
