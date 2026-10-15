from django.core.management.base import BaseCommand, CommandError

from core.employee_import import LABELS, EmployeeFileError, apply_plan, build_plan, read_rows


class Command(BaseCommand):
    help = ("Crea/aggiorna i dipendenti da un file Excel o CSV (Cognome, Nome, Azienda, Telefono, E-mail, "
            "Matricola facoltativa). Senza --apply mostra solo cosa cambierebbe.")

    def add_arguments(self, parser):
        parser.add_argument("file", help="Percorso del file .xlsx / .csv")
        parser.add_argument("--apply", action="store_true", help="Scrive davvero le modifiche nel database")
        parser.add_argument("--deactivate-missing", action="store_true",
                            help="Disattiva (is_active=False) i dipendenti di Kairos assenti dal file")
        parser.add_argument("--non-attivi", action="store_true", dest="inactive",
                            help="Ex dipendenti: li crea (o li porta) come NON attivi, non assegnabili nei piani")

    def handle(self, *args, **opts):
        try:
            with open(opts["file"], "rb") as fh:
                rows = read_rows(fh, opts["file"])
        except FileNotFoundError:
            raise CommandError(f"File non trovato: {opts['file']}")
        except EmployeeFileError as exc:
            raise CommandError(str(exc))

        if opts["inactive"] and opts["deactivate_missing"]:
            raise CommandError("--non-attivi e --deactivate-missing non si usano insieme.")
        plan = build_plan(rows, deactivate_missing=opts["deactivate_missing"], inactive=opts["inactive"])
        w = self.stdout.write
        w(f"Righe lette dal file: {plan.file_rows}")
        w(f"\nNUOVI: {len(plan.create)}" + ("  (creati NON attivi)" if plan.inactive else ""))
        for it in plan.create:
            w(f"  + {it['nome']} | {it['company'] or '—'} | {it['email']} | matricola {it['matricola']}")
        w(f"\nAGGIORNATI: {len(plan.update)}")
        for it in plan.update:
            ch = "; ".join(f"{LABELS[f]}: {o or '—'} -> {n}" for f, (o, n) in it["changes"].items())
            w(f"  ~ {it['nome']}: {ch}")
        w(f"\nInvariati: {plan.unchanged}")
        if plan.new_companies:
            w(f"Nuove aziende che verranno create: {', '.join(plan.new_companies)}")
        if plan.missing and not plan.inactive:
            w(f"\nIn Kairos ma non nel file: {len(plan.missing)}"
              + ("" if opts["deactivate_missing"] else " (restano invariati; --deactivate-missing per disattivarli)"))
            for it in plan.missing:
                w(f"  - {it['nome']}" + ("" if it["active"] else " (già disattivato)"))
        if plan.skipped:
            w(self.style.WARNING(f"\nRighe saltate: {len(plan.skipped)}"))
            for it in plan.skipped:
                w(self.style.WARNING(f"  ! riga {it['riga']} {it['nome']}: {it['motivo']}"))

        if not opts["apply"]:
            w(self.style.NOTICE("\nAnteprima: nessuna modifica scritta. Aggiungi --apply per applicare."))
            return
        res = apply_plan(plan)
        w(self.style.SUCCESS(f"\nApplicato: {res['create']} nuovi, {res['update']} aggiornati, "
                             f"{res['deactivate']} disattivati."))
