import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from reports.engine import MESI_IT
from reports.plan_import import apply_import, build_import
from reports.source_excel import ExcelFormatError


def _months(value: str):
    out = []
    for part in value.split(","):
        m = re.fullmatch(r"\s*(\d{4})-(\d{1,2})\s*", part)
        if not m or not 1 <= int(m[2]) <= 12:
            raise CommandError(f"Mese non valido: «{part}». Formato: 2026-10,2026-11")
        out.append((int(m[1]), int(m[2])))
    return out


class Command(BaseCommand):
    help = ("Importa uno o più mesi del piano turni ATI (.xlsm): per ogni mese crea il template dalla matrice "
            "posizioni x giorni, il piano dal template e le assegnazioni. Senza --apply mostra solo l'anteprima.")

    def add_arguments(self, parser):
        parser.add_argument("file", help="Percorso del piano turni (.xlsm / .xlsx)")
        parser.add_argument("--mesi", required=True, help="Mesi da importare, es. 2026-10,2026-11,2026-12")
        parser.add_argument("--apply", action="store_true", help="Scrive davvero nel database")
        parser.add_argument("--replace", action="store_true",
                            help="Se il piano del mese esiste già, lo cancella (con le assegnazioni) e lo ricrea")
        parser.add_argument("--user", help="Username registrato come autore dei piani (default: primo superuser)")
        parser.add_argument("--template-prefix", default="Template ATI", help="Prefisso del nome dei template")

    def handle(self, *args, **opts):
        months = _months(opts["mesi"])
        try:
            with open(opts["file"], "rb") as fh:
                plan = build_import(fh, months, opts["template_prefix"])
        except FileNotFoundError:
            raise CommandError(f"File non trovato: {opts['file']}")
        except ExcelFormatError as exc:
            raise CommandError(str(exc))

        w = self.stdout.write
        for mp in plan.months:
            w(f"\n=== {mp.plan_name}  (foglio «{mp.sheet}»)")
            w(f"  Template «{mp.template_name}»: {mp.positions} posizioni, {mp.spacers} separatori"
              + ("  [ESISTE GIÀ]" if mp.template_exists else ""))
            w(f"  Piano: {mp.assignments} assegnazioni, {mp.notes} con nota"
              + ("  [PIANO DEL MESE GIÀ PRESENTE]" if mp.plan_exists else ""))
            if mp.truncated_notes:
                w(f"  Note accorciate a 255 caratteri: {mp.truncated_notes}")
            if mp.double_booked:
                w(f"  Persona su più posizioni nello stesso giorno: {mp.double_booked} casi (importati così come sono)")
            if mp.unmatched:
                w(self.style.WARNING("  Nomi non trovati tra i dipendenti (celle saltate): "
                                     + ", ".join(f"{n} ×{c}" for n, c in mp.unmatched.most_common())))
            if mp.ambiguous:
                w(self.style.WARNING("  Nomi ambigui, più dipendenti possibili (celle saltate): "
                                     + ", ".join(f"{n} ×{c}" for n, c in mp.ambiguous.most_common())))
            if mp.orphans:
                w(f"  Commenti su celle senza nome (non importati): {len(mp.orphans)}")
                for o in mp.orphans[:10]:
                    w(f"    {o['cella']} {o['data']} {o['posizione'][:50]}: {o['testo'][:80]}")
        if plan.new_shift_types:
            w("\nTipi turno da creare: " + ", ".join(f"{c} ({v[0]})" for c, v in plan.new_shift_types.items()))

        if not opts["apply"]:
            w(self.style.NOTICE("\nAnteprima: nessuna modifica scritta. Aggiungi --apply per applicare."))
            return
        U = get_user_model()
        user = U.objects.filter(username=opts["user"]).first() if opts["user"] else \
            U.objects.filter(is_superuser=True).order_by("id").first()
        if user is None:
            raise CommandError("Nessun utente valido come autore (usa --user).")
        for r in apply_import(plan, user, replace=opts["replace"]):
            if r["esito"] == "creato":
                w(self.style.SUCCESS(f"{r['mese']}: creato piano #{r['plan_id']} ({r['righe']} righe, "
                                     f"{r['assegnazioni']} assegnazioni) dal template #{r['template_id']}"))
            else:
                w(self.style.WARNING(f"{r['mese']}: {r['esito']}"))
