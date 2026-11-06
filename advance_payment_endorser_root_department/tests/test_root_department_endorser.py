from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRootDepartmentEndorser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Users = env["res.users"].with_context(no_reset_password=True)
        Employee = env["hr.employee"]

        def person(name):
            user = Users.create({"name": name, "login": "aperd_%s" % name})
            return Employee.create({"name": name, "user_id": user.id})

        cls.dean = person("dean")
        cls.head = person("head")
        cls.borrower = person("borrower")
        cls.faculty = env["hr.department"].create(
            {"name": "Faculty", "manager_id": cls.dean.id}
        )
        cls.division = env["hr.department"].create(
            {"name": "Division", "parent_id": cls.faculty.id}
        )
        cls.borrower.write(
            {"department_id": cls.division.id, "parent_id": cls.head.id}
        )
        cls.dean.write({"department_id": cls.faculty.id, "parent_id": cls.head.id})

    def _make(self, employee):
        return self.env["advance.payment"].new({"employee_id": employee.id})

    def test_suggests_root_manager(self):
        self.assertEqual(self._make(self.borrower).endorser_id, self.dean.user_id)

    def test_root_manager_falls_back_to_line_manager(self):
        self.assertEqual(self._make(self.dean).endorser_id, self.head.user_id)

    def test_root_without_manager_suggests_nobody(self):
        self.faculty.manager_id = False
        self.assertFalse(self._make(self.borrower).endorser_id)
