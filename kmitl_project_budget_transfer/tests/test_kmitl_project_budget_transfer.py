from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKmitlProjectBudgetTransfer(TransactionCase):
    """The supported-project flag opens the project's analytic to every unit, and
    the transfer-line project picker narrows to projects matching the line."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPBT",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.ou = env.ref("operating_unit.main_operating_unit")
        cls.proj_ba = env["budget.account"].create(
            {
                "code": "KPBT_PROJBA",
                "name": "KPBT Project BA",
                "budget_type": "expense",
                "is_project": True,
                "project_type": "project",
            }
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def plan(code, name):
            return Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": name, "code": code}
            )

        def acc(name, code, plan_code, plan_name):
            return AA.create(
                {"name": name, "code": code, "plan_id": plan(plan_code, plan_name).id}
            )

        cls.dept = acc("Dept", "KPBT_DEPT", "departments", "Departments")
        cls.dept2 = acc("Dept2", "KPBT_DEPT2", "departments", "Departments")
        cls.source = acc("Source", "KPBT_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "KPBT_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "KPBT_FUND", "funds", "Funds")
        cls.fund2 = acc("Fund2", "KPBT_FUND2", "funds", "Funds")
        cls.proj_tag = acc("ProjTag", "KPBT_PROJ", "kmitl_project", "Project")

        cls.project = env["kmitl.project"].create(
            {
                "name": "KPBT Project",
                "project_type": "project",
                "operating_unit_id": cls.ou.id,
                "account_fiscal_year_id": cls.fy.id,
                "budget_account_id": cls.proj_ba.id,
                "analytic_account_id": cls.proj_tag.id,
                "activity_analytic_id": cls.activity.id,
                "department_analytic_id": cls.dept.id,
                "fund_analytic_id": cls.fund.id,
                "source_analytic_id": cls.source.id,
            }
        )

    # ------------------------------------------------------------------
    # Supported flag → analytic operating units
    # ------------------------------------------------------------------
    def test_flag_opens_and_restores_analytic_ou(self):
        self.project.write({"is_supported_by_other_units": False})
        self.assertEqual(self.proj_tag.operating_unit_ids, self.ou)
        self.project.is_supported_by_other_units = True
        self.assertFalse(self.proj_tag.operating_unit_ids)
        self.project.is_supported_by_other_units = False
        self.assertEqual(self.proj_tag.operating_unit_ids, self.ou)

    def test_flag_before_mint_opens_new_analytic(self):
        self.project.is_supported_by_other_units = True
        analytic = self.project._create_analytic_account_from_values(
            {"name": "KPBT Minted", "code": "KPBT_MINT"}
        )
        self.assertFalse(analytic.operating_unit_ids)
        self.project.is_supported_by_other_units = False
        analytic = self.project._create_analytic_account_from_values(
            {"name": "KPBT Minted 2", "code": "KPBT_MINT2"}
        )
        self.assertEqual(analytic.operating_unit_ids, self.ou)

    # ------------------------------------------------------------------
    # Transfer-line project picker
    # ------------------------------------------------------------------
    def _allowed(self, **vals):
        line = self.env["budget.move.line"].new(dict(vals, transfer_direction="to"))
        return line.allowed_kmitl_project_analytic_ids

    def test_picker_blank_dimensions_do_not_filter(self):
        self.assertIn(self.proj_tag, self._allowed())

    def test_picker_narrows_on_matching_dimensions(self):
        allowed = self._allowed(
            account_id=self.proj_ba.id,
            department_analytic_id=self.dept.id,
            activity_analytic_id=self.activity.id,
            fund_analytic_id=self.fund.id,
        )
        self.assertIn(self.proj_tag, allowed)

    def test_picker_excludes_mismatched_dimensions(self):
        self.assertNotIn(self.proj_tag, self._allowed(fund_analytic_id=self.fund2.id))
        self.assertNotIn(
            self.proj_tag, self._allowed(department_analytic_id=self.dept2.id)
        )

    def test_picker_filters_on_dialog_fiscal_year(self):
        # A dialog line has no move_id yet — the fiscal year comes from context.
        other_fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY-KPBT-OTHER",
                "date_from": date(2090, 10, 1),
                "date_to": date(2091, 9, 30),
                "company_id": self.env.company.id,
            }
        )
        Line = self.env["budget.move.line"]
        same = Line.with_context(transfer_fiscal_year_id=self.fy.id).new(
            {"transfer_direction": "to"}
        )
        self.assertIn(self.proj_tag, same.allowed_kmitl_project_analytic_ids)
        other = Line.with_context(transfer_fiscal_year_id=other_fy.id).new(
            {"transfer_direction": "to"}
        )
        self.assertNotIn(self.proj_tag, other.allowed_kmitl_project_analytic_ids)
