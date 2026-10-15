"""Profilo "Sola lettura": può consultare e scaricare, non può modificare né inviare email."""
import datetime as dt
import io
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Assignment, Employee, Plan, PlanRow, Profession, Reminder, ShiftType, Template
from core.readonly import READONLY_GROUP, is_readonly
from reports.models import EmployeeMedicalInfo
from reports.tests import make_ati_workbook


class ReadOnlyProfileTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.ro = U.objects.create_user("visitatore", password="pw-iniziale-123", is_staff=True)
        self.ro.groups.add(Group.objects.get_or_create(name=READONLY_GROUP)[0])
        self.emp = Employee.objects.create(first_name="Mario", last_name="Rossi", matricola="10", email="r@x.it")
        self.st = ShiftType.objects.create(code="M", label="Mattino", start_time=dt.time(6), end_time=dt.time(14))
        self.prof = Profession.objects.create(name="Preposto.1")
        self.plan = Plan.objects.create(month=10, year=2026, name="Ottobre 2026", created_by=self.boss)
        PlanRow.objects.create(plan=self.plan, order=1, duty="Preposto.1", shift_type=self.st)
        Assignment.objects.create(plan=self.plan, profession=self.prof, date=dt.date(2026, 10, 1),
                                  employee=self.emp, shift_type=self.st)
        self.client.force_login(self.ro)

    def api(self, action):
        return f"/api/plans/{self.plan.id}/{action}/"

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    # ---------------------------------------------------------------- consultazione
    def test_flag(self):
        self.assertTrue(is_readonly(self.ro))
        self.assertFalse(is_readonly(self.boss))
        admin = get_user_model().objects.create_superuser("root", password="x")
        admin.groups.add(Group.objects.get(name=READONLY_GROUP))
        self.assertFalse(is_readonly(admin))   # un amministratore non è mai limitato

    def test_can_view_everything(self):
        for name, args in [("home", []), ("plans_area", []), ("templates_area", []), ("calendar_notes", []),
                           ("monthly_plan", [self.plan.id]), ("employees-directory", []), ("analytics-overview", []),
                           ("reports:report_commessa", []), ("profile", []), ("password_change", [])]:
            r = self.client.get(reverse(name, args=args))
            self.assertEqual(r.status_code, 200, name)
        self.assertEqual(self.client.get(self.api("grid")).status_code, 200)
        self.assertEqual(self.client.get("/api/reminders/").status_code, 200)

    def test_badge_and_hidden_controls(self):
        r = self.client.get(reverse("monthly_plan", args=[self.plan.id]))
        self.assertContains(r, "ro-mode")
        self.assertContains(r, "Sola lettura")
        self.assertContains(r, 'class="grid-actions ro-hide"')
        self.client.force_login(self.boss)
        r = self.client.get(reverse("monthly_plan", args=[self.plan.id]))
        self.assertNotContains(r, "ro-mode")
        self.assertNotContains(r, "ro-badge")

    def test_downloads_allowed(self):
        r = self.client.get(self.api("export_xlsx"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheet", r["Content-Type"])
        self.assertEqual(self.client.get(reverse("reports:kairos_dataset") + "?year=2026").status_code, 200)
        f = SimpleUploadedFile("p.xlsx", make_ati_workbook())
        self.assertEqual(self.client.post(reverse("reports:excel_dataset"), {"file": f}).status_code, 200)

    def test_prescription_import_preview_only(self):
        url = reverse("reports:import_prescriptions")
        r = self.client.post(url, {"file": SimpleUploadedFile("p.xlsx", make_ati_workbook()), "mode": "preview"})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(url, {"file": SimpleUploadedFile("p.xlsx", make_ati_workbook()), "mode": "apply"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(EmployeeMedicalInfo.objects.exists())

    def test_password_change_allowed(self):
        r = self.client.post(reverse("password_change"), {
            "old_password": "pw-iniziale-123", "new_password1": "Nuova-Pass-2026!", "new_password2": "Nuova-Pass-2026!"})
        self.assertEqual(r.status_code, 302)

    def test_logout_allowed(self):
        self.client.get("/logout/")
        self.assertEqual(self.client.get(reverse("reports:report_commessa")).status_code, 302)

    # ---------------------------------------------------------------- blocchi
    def test_plan_writes_blocked(self):
        d = {"profession_id": self.prof.id, "date": "2026-10-02", "employee_id": self.emp.id}
        for action, body in [("bulk_assign", {"cells": [d], "employee_id": self.emp.id}),
                             ("bulk_clear", {"cells": [{"profession_id": self.prof.id, "date": "2026-10-01"}]}),
                             ("set_note", {"profession_id": self.prof.id, "date": "2026-10-01", "note": "x"})]:
            r = self.post_json(self.api(action), body)
            self.assertEqual(r.status_code, 403, action)
            self.assertIn("sola lettura", r.json()["detail"])
        self.assertEqual(Assignment.objects.count(), 1)
        self.assertEqual(Assignment.objects.get().notes or "", "")
        self.assertEqual(self.client.delete(f"/api/plans/{self.plan.id}/").status_code, 403)
        self.assertTrue(Plan.objects.filter(pk=self.plan.id).exists())

    def test_no_emails(self):
        for action in ("notify", "broadcast_xlsx"):
            self.assertEqual(self.post_json(self.api(action), {}).status_code, 403, action)
        self.assertEqual(self.client.post(reverse("turn_pattern_forecast"), {}).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_create_pages_blocked(self):
        for name in ("plan_create", "template_create", "turn_pattern_forecast"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 403, name)
            self.assertContains(r, "Profilo in sola lettura", status_code=403)
        self.client.post(reverse("plan_create"), {"month": 11, "year": 2026})
        self.client.post(reverse("template_create"), {"name": "X"})
        self.assertEqual(Plan.objects.count(), 1)
        self.assertFalse(Template.objects.exists())

    def test_other_writes_blocked(self):
        self.assertEqual(self.post_json("/api/reminders/", {"date": "2026-10-01", "title": "x"}).status_code, 403)
        self.assertFalse(Reminder.objects.exists())
        self.assertEqual(self.post_json("/api/employees/", {"first_name": "X"}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/employees/{self.emp.id}/").status_code, 403)
        url = reverse("reports:save_prescriptions", args=[self.emp.id])
        self.assertEqual(self.post_json(url, {"text": "x"}).status_code, 403)
        self.assertFalse(EmployeeMedicalInfo.objects.exists())
        self.assertEqual(self.client.get("/admin/").status_code, 302)   # admin: solo superuser

    def test_staff_not_affected(self):
        self.client.force_login(self.boss)
        self.assertEqual(self.client.get(reverse("plan_create")).status_code, 200)
        r = self.post_json(self.api("set_note"), {"profession_id": self.prof.id, "date": "2026-10-01", "note": "ok"})
        self.assertEqual(r.status_code, 200)

    # ---------------------------------------------------------------- comando
    def test_command(self):
        call_command("utente_sola_lettura", "ospite", "--password", "x", "--nome", "Ospite", stdout=io.StringIO())
        u = get_user_model().objects.get(username="ospite")
        self.assertTrue(u.is_staff and not u.is_superuser and is_readonly(u))
        call_command("utente_sola_lettura", "ospite", "--rimuovi", stdout=io.StringIO())
        u = get_user_model().objects.get(username="ospite")
        self.assertFalse(is_readonly(u))
        self.assertTrue(u.is_staff)
