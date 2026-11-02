from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectAnnex(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPTP",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "KPTP_SRC", "name": "KPTP Src", "budget_type": "expense"}
        )
        cls.proj_ba = BA.create(
            {
                "code": "KPTP_PROJBA",
                "name": "KPTP Project BA",
                "budget_type": "expense",
                "is_project": True,
                "project_type": "project",
            }
        )
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code, plan_name):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_name, "code": plan_code}
            )
            return AA.create({"name": name, "code": code, "plan_id": plan.id})

        cls.dept = acc("Dept", "KPTP_DEPT", "departments", "Departments")
        cls.source = acc("Source", "KPTP_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "KPTP_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "KPTP_FUND", "funds", "Funds")
        cls.proj_tag = acc("ProjTag", "KPTP_PROJ", "kmitl_project", "Project")
        cls.project = env["kmitl.project"].create(
            {
                "name": "KPTP Project",
                "project_type": "project",
                "operating_unit_id": env.ref("operating_unit.main_operating_unit").id,
                "account_fiscal_year_id": cls.fy.id,
                "budget_account_id": cls.proj_ba.id,
                "analytic_account_id": cls.proj_tag.id,
            }
        )
        cls.cat = env["project.budget.category"].create({"name": "KPTP Cat"})
        env["project.budget.line"].create(
            [
                {
                    "project_id": cls.project.id,
                    "budget_type": "expense",
                    "name": "KPTP Line %s" % i,
                    "category_id": cls.cat.id,
                    "amount": 100 * i,
                }
                for i in (1, 2)
            ]
        )

    def _transfer(self, tagged_amounts):
        dims = {
            "department_analytic_id": self.dept.id,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
        }
        lines = [
            Command.create(
                dict(
                    dims,
                    transfer_direction="from",
                    account_id=self.src.id,
                    amount=sum(tagged_amounts),
                )
            )
        ]
        for amount in tagged_amounts:
            lines.append(
                Command.create(
                    dict(
                        dims,
                        transfer_direction="to",
                        account_id=self.proj_ba.id,
                        kmitl_project_analytic_id=self.proj_tag.id,
                        amount=amount,
                    )
                )
            )
        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": lines,
            }
        )

    def test_lines_of_one_project_collapse_with_expense_plan(self):
        annex = self._transfer([1000, 500])._annex_projects()
        self.assertEqual(len(annex), 1)
        label, rows = annex[0]
        self.assertIn("โอนเข้า", label)
        self.assertEqual(len(rows), 1)
        project, amount, groups = rows[0]
        self.assertEqual((project, amount), (self.project, 1500.0))
        self.assertEqual(len(groups), 1)
        self.assertEqual([ln.amount for ln in groups[0][1]], [100.0, 200.0])

    def test_pdf_renders_with_annex(self):
        transfer = self._transfer([1000])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "budget_transfer_pdf.report_budget_transfer", transfer.ids
        )
        self.assertIn("รายละเอียดโครงการ/กิจกรรม", html.decode())
        self.assertIn("KPTP Line 1", html.decode())
