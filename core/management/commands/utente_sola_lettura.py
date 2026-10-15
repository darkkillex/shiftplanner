"""
Crea o configura un utente con profilo "Sola lettura".

    python manage.py utente_sola_lettura mario.rossi                 # crea (chiede la password) o converte
    python manage.py utente_sola_lettura mario.rossi --password X --nome Mario --cognome Rossi --email m@x.it
    python manage.py utente_sola_lettura mario.rossi --rimuovi       # toglie il profilo (torna staff normale)
    python manage.py utente_sola_lettura --elenco                    # utenti in sola lettura

Un utente in sola lettura è staff (vede tutti i moduli) ma non può modificare
nulla né inviare email; può scaricare gli Excel dei piani e le statistiche
del Report commessa. Lo stesso risultato si ottiene dall'Area Amministratore
spuntando "Staff" e aggiungendo l'utente al gruppo "Sola lettura".
"""
import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from core.readonly import READONLY_GROUP


class Command(BaseCommand):
    help = 'Crea o configura un utente con profilo "Sola lettura".'

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?")
        parser.add_argument("--password")
        parser.add_argument("--nome", default="")
        parser.add_argument("--cognome", default="")
        parser.add_argument("--email", default="")
        parser.add_argument("--rimuovi", action="store_true", help="toglie il profilo sola lettura")
        parser.add_argument("--elenco", action="store_true", help="elenca gli utenti in sola lettura")

    def handle(self, *args, **o):
        group, _ = Group.objects.get_or_create(name=READONLY_GROUP)
        User = get_user_model()

        if o["elenco"]:
            users = group.user_set.order_by("username")
            if not users:
                self.stdout.write("Nessun utente in sola lettura.")
            for u in users:
                stato = "attivo" if u.is_active else "disattivato"
                self.stdout.write(f"- {u.username} ({u.get_full_name() or '—'}, {stato})")
            return

        username = o["username"]
        if not username:
            raise CommandError("Indica lo username (oppure --elenco).")

        if o["rimuovi"]:
            try:
                u = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"Utente «{username}» inesistente.")
            u.groups.remove(group)
            self.stdout.write(self.style.SUCCESS(f"«{username}» non è più in sola lettura (resta staff)."))
            return

        u = User.objects.filter(username=username).first()
        created = u is None
        if created:
            pwd = o["password"]
            if not pwd:
                pwd = getpass.getpass(f"Password per {username}: ")
                if pwd != getpass.getpass("Ripeti la password: "):
                    raise CommandError("Le password non coincidono.")
            if not pwd:
                raise CommandError("Password vuota.")
            u = User(username=username)
            u.set_password(pwd)
        elif o["password"]:
            u.set_password(o["password"])
        if u.is_superuser:
            raise CommandError(f"«{username}» è un amministratore: non può essere messo in sola lettura.")
        if o["nome"]:
            u.first_name = o["nome"]
        if o["cognome"]:
            u.last_name = o["cognome"]
        if o["email"]:
            u.email = o["email"]
        u.is_staff = True
        u.is_active = True
        u.save()
        u.groups.add(group)
        verb = "creato" if created else "aggiornato"
        self.stdout.write(self.style.SUCCESS(f"Utente «{username}» {verb} con profilo Sola lettura."))
