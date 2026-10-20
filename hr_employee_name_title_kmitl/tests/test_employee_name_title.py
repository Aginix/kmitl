from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEmployeeNameTitle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env["hr.employee"]
        cls.asst_prof = cls.env.ref(
            "hr_employee_academic_standing_thailand.AS03"
        )  # ผู้ช่วยศาสตราจารย์ / Assistant Professor
        cls.prof = cls.env.ref(
            "hr_employee_academic_standing_thailand.AS01"
        )  # ศาสตราจารย์
        cls.prefix_mr = cls.env.ref("kmitl_hr_employee_full_name.003")  # นาย

    def test_academic_prefix_glued_to_firstname(self):
        emp = self.Employee.create(
            {"firstname": "สมชาย", "lastname": "ใจดี", "role": "academic"}
        )
        emp.academic_standing_id = self.asst_prof
        self.assertEqual(emp.academic_standing_title, "ผู้ช่วยศาสตราจารย์")
        self.assertEqual(emp.name, "ผู้ช่วยศาสตราจารย์สมชาย ใจดี")
        self.assertEqual(emp.firstname, "สมชาย")
        self.assertEqual(emp.lastname, "ใจดี")

    def test_changing_standing_does_not_stack(self):
        emp = self.Employee.create(
            {"firstname": "สมชาย", "lastname": "ใจดี", "role": "academic"}
        )
        emp.academic_standing_id = self.asst_prof
        emp.academic_standing_id = self.prof
        self.assertEqual(emp.name, "ศาสตราจารย์สมชาย ใจดี")
        self.assertNotIn("ผู้ช่วย", emp.name)

    def test_support_uses_personal_prefix(self):
        emp = self.Employee.create(
            {"firstname": "สมชาย", "lastname": "ใจดี", "prefix_id": self.prefix_mr.id}
        )
        self.assertEqual(emp.name, "นายสมชาย ใจดี")

    def test_direct_name_write_does_not_corrupt_parts(self):
        emp = self.Employee.create(
            {"firstname": "สมชาย", "lastname": "ใจดี", "prefix_id": self.prefix_mr.id}
        )
        emp.write({"name": "Hacked Name"})
        # The inverse is dropped, so parts stay intact and the name is re-derived.
        self.assertEqual(emp.firstname, "สมชาย")
        self.assertEqual(emp.lastname, "ใจดี")
        self.assertEqual(emp.name, "นายสมชาย ใจดี")

    def test_name_only_create_seeds_parts(self):
        emp = self.Employee.create({"name": "สมหญิง รักเรียน"})
        # full_name's create-time split still seeds the parts (hybrid).
        self.assertEqual(emp.firstname, "สมหญิง")
        self.assertEqual(emp.lastname, "รักเรียน")
        self.assertEqual(emp.name, "สมหญิง รักเรียน")

    def test_secondary_english_name(self):
        emp = self.Employee.create(
            {
                "firstname": "สมชาย",
                "lastname": "ใจดี",
                "firstname_secondary": "Somchai",
                "lastname_secondary": "Jaidee",
                "role": "academic",
            }
        )
        emp.academic_standing_id = self.asst_prof
        # English keeps a space between title and name.
        self.assertEqual(emp.name_secondary, "Assistant Professor Somchai Jaidee")

    def test_no_parts_fallbacks_to_untitled(self):
        emp = self.Employee.create({"role": "academic"})
        emp.academic_standing_id = self.asst_prof
        self.assertEqual(emp.name, "Untitled")

    def test_onchange_live_preview(self):
        # Picking the academic standing updates the name live in the form,
        # not only on save.
        form = Form(self.Employee)
        form.firstname = "สมชาย"
        form.lastname = "ใจดี"
        form.role = "academic"
        self.assertEqual(form.name, "สมชาย ใจดี")
        form.academic_standing_id = self.asst_prof
        self.assertEqual(form.name, "ผู้ช่วยศาสตราจารย์สมชาย ใจดี")
        form.academic_standing_id = self.prof
        self.assertEqual(form.name, "ศาสตราจารย์สมชาย ใจดี")
        emp = form.save()
        self.assertEqual(emp.name, "ศาสตราจารย์สมชาย ใจดี")
