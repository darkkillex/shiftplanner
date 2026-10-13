from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from reports.presc_import import apply_plan, build_plan, read_file_prescriptions
from reports.source_excel import ExcelFormatError


class Command(BaseCommand):
    help = ("Importa in Kairos le prescrizioni mediche dal foglio 'Dipendenti' del piano turni ATI. "
            "Senza --apply mostra solo cosa cambierebbe.")

    def add_arguments(self, parser):
        parser.add_argument("file", help="Percorso del piano turni (.xlsm / .xlsx)")
        parser.add_argument("--apply", action="store_true", help="Scrive davvero le modifiche nel database")
        parser.add_argument("--clear-missing", action="store_true",
                            help="Rimuove da Kairos le prescrizioni che nel file sono vuote")
        parser.add_argument("--user", help="Username da registrare come autore della modifica")

    @staticmethod
    def _one_line(t):
        return " / ".join(x.strip() for x in (t or "").splitlines() if x.strip())

    def handle(self, *args, **opts):
        try:
            with open(opts["file"], "rb") as fh:
                rows = read_file_prescriptions(fh)
        except FileNotFoundError:
            raise CommandError(f"File non trovato: {opts['file']}")
        except ExcelFormatError as exc:
            raise CommandError(str(exc))

        plan = build_plan(rows, clear_missing=opts["clear_missing"])
        w = self.stdout.write
        w(f"Righe nel foglio Dipendenti: {plan.file_rows} (con prescrizione: {plan.file_with_presc})")
        for label, items in (("NUOVE", plan.create), ("AGGIORNATE", plan.update), ("RIMOSSE", plan.clear)):
            w(f"\n{label}: {len(items)}")
            for it in items:
                old, new = self._one_line(it["old"]), self._one_line(it["new"])
                w(f"  - {it['nome']}: {old or '—'}  ->  {new or '(vuota)'}" if label != "NUOVE"
                  else f"  - {it['nome']}: {new}")
        w(f"\nInvariate: {plan.unchanged}")
        if plan.kept:
            w(f"Vuote nel file ma presenti in Kairos (mantenute, usa --clear-missing per rimuoverle): "
              f"{', '.join(i['nome'] for i in plan.kept)}")
        if plan.not_found:
            w(self.style.WARNING(f"Non trovati in Kairos: {', '.join(plan.not_found)}"))
        if plan.ambiguous:
            w(self.style.WARNING(f"Omonimi in Kairos, saltati: {', '.join(plan.ambiguous)}"))

        if not opts["apply"]:
            w(self.style.NOTICE("\nAnteprima: nessuna modifica scritta. Aggiungi --apply per applicare."))
            return
        user = None
        if opts["user"]:
            user = get_user_model().objects.filter(username=opts["user"]).first()
            if not user:
                raise CommandError(f"Utente non trovato: {opts['user']}")
        res = apply_plan(plan, user)
        w(self.style.SUCCESS(f"\nApplicato: {res['create']} nuove, {res['update']} aggiornate, {res['clear']} rimosse."))
