from datetime import date

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOrganizerDepartment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-ORG",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )
        plan = env["account.analytic.plan"].search(
            [("code", "=", "departments")], limit=1
        ) or env["account.analytic.plan"].create(
            {"name": "departments", "code": "departments"}
        )
        AA = env["account.analytic.account"]
        cls.dept_budget = AA.create({"name": "Org Rector Office", "plan_id": plan.id})
        cls.dept_organizer = AA.create({"name": "Org Engineering", "plan_id": plan.id})
        cls.dept_other = AA.create({"name": "Org Other", "plan_id": plan.id})

    def _make_project(self):
        return self.env["kmitl.project"].create(
            {
                "name": "Organizer Project",
                "account_fiscal_year_id": self.fiscal_year.id,
                "department_analytic_id": self.dept_budget.id,
            }
        )

    def test_defaults_to_budget_department(self):
        project = self._make_project()
        self.assertEqual(project.organizer_department_id, self.dept_budget)

    def test_kept_when_budget_department_changes(self):
        project = self._make_project()
        project.organizer_department_id = self.dept_organizer
        project.write({"analytic_distribution": {str(self.dept_other.id): 100}})
        self.assertEqual(project.department_analytic_id, self.dept_other)
        self.assertEqual(project.organizer_department_id, self.dept_organizer)

    def test_kept_when_budget_department_changes_in_form(self):
        project = self._make_project()
        project.organizer_department_id = self.dept_organizer
        with Form(project) as form:
            form.department_analytic_id = self.dept_other
            self.assertEqual(form.organizer_department_id, self.dept_organizer)
        self.assertEqual(project.organizer_department_id, self.dept_organizer)
