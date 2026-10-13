import datetime as dt
import io
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Assignment, Company, Employee, Plan, PlanRow, Profession, ShiftType

from .models import EmployeeMedicalInfo
from .source_excel import build_from_excel
from .source_kairos import build_from_kairos


def make_ati_workbook() -> bytes:
    """Piano turni ATI minimale: 1 foglio mese (marzo 2026, 3 giorni), foglio Dipendenti e MAIN."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment

    wb = Workbook()
    ws = wb.active
    ws.title = "Marzo 2026"
    ws["A1"], ws["B1"] = "Numero mese", 3
    for k in range(3):
        ws.cell(row=1, column=8 + k, value=dt.datetime(2026, 3, 1 + k))
        ws.cell(row=2, column=8 + k, value=dt.datetime(2026, 3, 1 + k))
    ws["D3"], ws["E3"] = "TURNO DI LAVORO", "POSIZIONE"
    # matrice posizioni x giorni
    ws["D4"], ws["E4"] = "D", "Ufficio - Preposto"
    ws["H4"], ws["I4"], ws["J4"] = "Rossi Mario", "Rossi Mario", "Assenza"
    ws["I4"].comment = Comment("Permesso dalle 15:00 alle 17:00", "Tester")
    ws["D5"], ws["E5"] = "F", "Ferie"
    ws["H5"] = "Bianchi Anna"
    # blocco dipendenti (riga 813 nel file reale; qui basta che ci sia la riga DIPENDENTE)
    ws["E20"], ws["F20"] = "DIPENDENTE", "Azienda"
    rows = [("Rossi Mario", "Rina", ["D", "D", "-"], ["Ufficio - Preposto\n - ", "Ufficio - Preposto\n - ", "-\n-"]),
            ("Bianchi Anna", "Sivam", ["F", "ERROR", "C"], ["Ferie\n - ", "ERROR", "Operatore\n - "])]
    r = 21
    for nome, soc, codes, mans in rows:
        ws.cell(row=r, column=5, value=nome); ws.cell(row=r, column=6, value=soc)
        ws.cell(row=r + 1, column=5, value=nome); ws.cell(row=r + 1, column=6, value=soc)
        for k in range(3):
            ws.cell(row=r, column=8 + k, value=codes[k])
            ws.cell(row=r + 1, column=8 + k, value=mans[k])
        r += 2
    ana = wb.create_sheet("Dipendenti")
    ana.append(["Cognome", "Nome", "Nome su ROTA", "Società", "Prescrizioni Mediche", "Telefono Mobile", "Email Aziendale", "Senior/Junior"])
    ana.append(["Rossi", "Mario", "Rossi Mario", "Rina", "No MMC > 10 kg", "333", "m.rossi@x.it", "Senior"])
    ana.append(["Bianchi", "Anna", "Bianchi Anna", "Sivam", None, None, "a.bianchi@x.it", "Junior"])
    main = wb.create_sheet("MAIN")
    main["J3"], main["K3"] = "D", "08,00-17,00"
    main["J4"], main["K4"] = "C", "22,00-06,00"
    hidden = wb.create_sheet("Master")
    hidden["A1"], hidden["B1"] = "Numero mese", 6
    hidden.sheet_state = "veryHidden"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ExcelSourceTests(TestCase):
    def test_parse_ati_format(self):
        ds = build_from_excel(io.BytesIO(make_ati_workbook()), "piano.xlsx", {})
        self.assertEqual(ds["months"], ["2026-03"])
        people = {p["n"]: i for i, p in enumerate(ds["people"])}
        self.assertNotIn("Assenza", people)                       # segnaposto, non persona
        rossi = ds["people"][people["Rossi Mario"]]
        self.assertEqual(rossi["presc"], "No MMC > 10 kg")
        self.assertEqual(rossi["soc"], "Rina")
        self.assertEqual(rossi["liv"], "Senior")
        rec = {(ds["people"][r[0]]["n"], r[1]): r for r in ds["rec"]}
        d1 = rec[("Rossi Mario", "2026-03-01")]
        self.assertEqual((d1[2], d1[3], d1[4]), ("D", "lavoro", 9.0))   # ore dal foglio MAIN
        self.assertGreaterEqual(d1[6], 0)                                 # preposto
        d2 = rec[("Rossi Mario", "2026-03-02")]
        self.assertEqual(d2[7], "Permesso dalle 15:00 alle 17:00")        # nota di cella
        self.assertEqual(d2[8], "Tester")
        self.assertEqual(rec[("Rossi Mario", "2026-03-03")][3], "riposo")
        self.assertEqual(rec[("Bianchi Anna", "2026-03-01")][3:5], ["ferie", 8])
        self.assertEqual(rec[("Bianchi Anna", "2026-03-02")][3:5], ["anomalia", 0])
        self.assertEqual(rec[("Bianchi Anna", "2026-03-03")][3], "notte")
        self.assertEqual(len(ds["prep"]), 2)
        self.assertTrue(any("nascosto" in d["esito"] for d in ds["diag"]))

    def test_rejects_unknown_format(self):
        from openpyxl import Workbook
        from .source_excel import ExcelFormatError
        buf = io.BytesIO(); Workbook().save(buf); buf.seek(0)
        with self.assertRaises(ExcelFormatError):
            build_from_excel(buf, "vuoto.xlsx", {})


class KairosSourceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("boss", password="x", is_staff=True)
        rina = Company.objects.create(name="RINA Consulting S.p.a.")
        self.e1 = Employee.objects.create(first_name="Mario", last_name="Rossi", matricola="1", email="a@x.it", company=rina)
        self.e2 = Employee.objects.create(first_name="Anna", last_name="Bianchi", matricola="2", email="b@x.it", company=rina)
        st_a = ShiftType.objects.create(code="A", label="Turno A", start_time=dt.time(6), end_time=dt.time(14))
        st_c = ShiftType.objects.create(code="C", label="Turno C", start_time=dt.time(22), end_time=dt.time(6))
        plan = Plan.objects.create(month=3, year=2026, name="Marzo", created_by=self.user)
        p_prep = Profession.objects.create(name="Ufficio - Preposto.1")
        p_fer = Profession.objects.create(name="Ferie.1")
        PlanRow.objects.create(plan=plan, order=1, duty="Ufficio - Preposto.1", shift_type=st_a)
        PlanRow.objects.create(plan=plan, order=2, duty="Ferie.1")
        Assignment.objects.create(plan=plan, profession=p_prep, date=dt.date(2026, 3, 2), employee=self.e1, shift_type=st_c, notes="nota")
        Assignment.objects.create(plan=plan, profession=p_fer, date=dt.date(2026, 3, 2), employee=self.e2)
        EmployeeMedicalInfo.objects.create(employee=self.e1, prescriptions="Prescrizione X")

    def test_dataset(self):
        ds = build_from_kairos(2026)
        self.assertEqual(ds["months"], ["2026-03"])
        people = {p["n"]: p for p in ds["people"]}
        self.assertEqual(people["Rossi Mario"]["presc"], "Prescrizione X")
        self.assertEqual(people["Rossi Mario"]["soc"], "Rina")
        rec = {(ds["people"][r[0]]["n"], r[1]): r for r in ds["rec"]}
        r = rec[("Rossi Mario", "2026-03-02")]
        self.assertEqual((r[2], r[3], r[4]), ("C", "notte", 8.0))      # ore dagli orari del turno
        self.assertEqual(ds["mans"][r[5]], "Ufficio - Preposto")       # senza suffisso .1
        self.assertGreaterEqual(r[6], 0)
        self.assertEqual(r[7], "nota")
        self.assertEqual(rec[("Bianchi Anna", "2026-03-02")][2:4], ["F", "ferie"])   # dal nome riga
        self.assertEqual(rec[("Bianchi Anna", "2026-03-03")][3], "riposo")
        self.assertEqual(len([x for x in ds["rec"] if ds["people"][x[0]]["n"] == "Rossi Mario"]), 31)
        self.assertEqual(len(ds["prep"]), 1)


class PermissionTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user("staff", password="x", is_staff=True)
        self.user = U.objects.create_user("user", password="x")
        self.emp = Employee.objects.create(first_name="A", last_name="B", matricola="9", email="z@x.it")

    def test_page_and_home_card(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("reports:report_commessa")).status_code, 302)
        self.assertNotContains(self.client.get(reverse("home")), "Report commessa")
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("reports:report_commessa")).status_code, 200)
        self.assertContains(self.client.get(reverse("home")), "Report commessa")

    def test_api_forbidden_for_normal_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("reports:kairos_dataset")).status_code, 403)
        f = SimpleUploadedFile("p.xlsx", make_ati_workbook())
        self.assertEqual(self.client.post(reverse("reports:excel_dataset"), {"file": f}).status_code, 403)
        url = reverse("reports:save_prescriptions", args=[self.emp.id])
        self.assertEqual(self.client.post(url, '{"text":"x"}', content_type="application/json").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("reports:kairos_dataset")).status_code, 401)

    def test_staff_api(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("reports:kairos_dataset") + "?year=2026").status_code, 200)
        f = SimpleUploadedFile("p.xlsx", make_ati_workbook())
        r = self.client.post(reverse("reports:excel_dataset"), {"file": f})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.content)["source"]["kind"], "excel")
        bad = SimpleUploadedFile("p.csv", b"a;b")
        self.assertEqual(self.client.post(reverse("reports:excel_dataset"), {"file": bad}).status_code, 400)

    def test_save_and_clear_prescriptions(self):
        self.client.force_login(self.staff)
        url = reverse("reports:save_prescriptions", args=[self.emp.id])
        r = self.client.post(url, json.dumps({"text": "  Niente turni notturni  "}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        info = EmployeeMedicalInfo.objects.get(employee=self.emp)
        self.assertEqual((info.prescriptions, info.updated_by), ("Niente turni notturni", self.staff))
        self.client.post(url, json.dumps({"text": ""}), content_type="application/json")
        self.assertFalse(EmployeeMedicalInfo.objects.filter(employee=self.emp).exists())

    def test_prescriptions_not_in_employee_api(self):
        # le prescrizioni non devono finire nell'API /api/employees/ (aperta a tutti gli utenti)
        from core.serializers import EmployeeSerializer
        self.assertNotIn("medical_info", EmployeeSerializer.Meta.fields)
        self.assertNotIn("prescriptions", EmployeeSerializer.Meta.fields)


class PrescriptionImportTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user("staff2", password="x", is_staff=True)
        self.rossi = Employee.objects.create(first_name="Mario", last_name="Rossi", matricola="10", email="r@x.it")
        self.bianchi = Employee.objects.create(first_name="Anna", last_name="Bianchi", matricola="11", email="b@x.it")
        EmployeeMedicalInfo.objects.create(employee=self.bianchi, prescriptions="Vecchia prescrizione")

    def test_preview_then_apply(self):
        from .presc_import import apply_plan, build_plan, read_file_prescriptions
        rows = read_file_prescriptions(io.BytesIO(make_ati_workbook()))
        plan = build_plan(rows)
        self.assertEqual([i["nome"] for i in plan.create], ["Rossi Mario"])
        self.assertEqual([i["nome"] for i in plan.kept], ["Bianchi Anna"])   # vuota nel file: mantenuta
        self.assertFalse(EmployeeMedicalInfo.objects.filter(employee=self.rossi).exists())   # anteprima: nulla scritto
        apply_plan(plan, self.staff)
        self.assertEqual(self.rossi.medical_info.prescriptions, "No MMC > 10 kg")
        self.assertEqual(EmployeeMedicalInfo.objects.get(employee=self.bianchi).prescriptions, "Vecchia prescrizione")
        plan2 = build_plan(rows, clear_missing=True)
        self.assertEqual((plan2.unchanged, len(plan2.clear)), (1, 1))
        apply_plan(plan2)
        self.assertFalse(EmployeeMedicalInfo.objects.filter(employee=self.bianchi).exists())

    def test_endpoint(self):
        url = reverse("reports:import_prescriptions")
        self.client.force_login(self.staff)
        r = self.client.post(url, {"file": SimpleUploadedFile("p.xlsx", make_ati_workbook()), "mode": "preview"})
        self.assertEqual(json.loads(r.content)["changes"], 1)
        self.assertFalse(EmployeeMedicalInfo.objects.filter(employee=self.rossi).exists())
        r = self.client.post(url, {"file": SimpleUploadedFile("p.xlsx", make_ati_workbook()), "mode": "apply"})
        self.assertEqual(json.loads(r.content)["applied"]["create"], 1)
        self.assertEqual(EmployeeMedicalInfo.objects.get(employee=self.rossi).updated_by, self.staff)
        user = get_user_model().objects.create_user("plain", password="x")
        self.client.force_login(user)
        r = self.client.post(url, {"file": SimpleUploadedFile("p.xlsx", make_ati_workbook()), "mode": "apply"})
        self.assertEqual(r.status_code, 403)
