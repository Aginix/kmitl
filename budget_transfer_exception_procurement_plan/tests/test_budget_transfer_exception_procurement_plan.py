from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged

POPUP_MODEL = "budget.transfer.exception.confirm"


@tagged("post_install", "-at_install")
class TestBudgetTransferExceptionProcurementPlan(TransactionCase):
    """On ยืนยัน (action_submit), a transfer line whose budget code is a
    procurement-plan code (``procurement_plan``) must match its
    ``procurement.plan`` source — same budget code, same fiscal year, and same
    four core dimensions — else the base.exception review popup is raised."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-TREXP",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.fy2 = env["account.fiscal.year"].create(
            {
                "name": "FY-TREXP-2",
                "date_from": date(2026, 10, 1),
                "date_to": date(2027, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "TRP_SRC", "name": "Src", "budget_type": "expense"}
        )
        cls.proc_ba = BA.create(
            {
                "code": "TRP_PROCBA",
                "name": "Procurement BA",
                "budget_type": "expense",
                "procurement_plan": True,
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

        cls.dept = acc("Dept", "TRP_DEPT", "departments", "Departments")
        cls.source = acc("Source", "TRP_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "TRP_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "TRP_FUND", "funds", "Funds")
        cls.fund2 = acc("Fund2", "TRP_FUND2", "funds", "Funds")
        cls.proc_tag = acc("ProcTag", "TRP_PROC", "procurement_plan", "Procurement")

        # The source-of-truth plan the transfer must agree with. Seeding
        # analytic_distribution populates the convenience dims + analytic_account_id
        # (kmitl analytic mixin), so it is searchable by the procurement tag.
        cls.plan_rec = env["procurement.plan"].create(
            {
                "description": "Test Plan",
                "amount": 1000,
                "unit": "ชุด",
                "account_fiscal_year_id": cls.fy.id,
                "budget_account_id": cls.proc_ba.id,
                "analytic_distribution": {
                    str(cls.activity.id): 100,
                    str(cls.dept.id): 100,
                    str(cls.fund.id): 100,
                    str(cls.source.id): 100,
                    str(cls.proc_tag.id): 100,
                },
            }
        )

        cls._appropriate(cls.src, 1000)

    @classmethod
    def _appropriate(cls, account, amount):
        move = cls.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": cls.fy.id,
                "department_analytic_id": cls.dept.id,
                "source_analytic_id": cls.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "balance": amount,
                            "activity_analytic_id": cls.activity.id,
                            "fund_analytic_id": cls.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _transfer(self, to_line, fy=None):
        from_line = {
            "transfer_direction": "from",
            "account_id": self.src.id,
            "amount": 1000,
            "department_analytic_id": self.dept.id,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
        }
        to_line = dict(to_line, transfer_direction="to", amount=1000)
        to_line.setdefault("department_analytic_id", self.dept.id)
        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": (fy or self.fy).id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "reason": "test",
                "line_ids": [Command.create(from_line), Command.create(to_line)],
            }
        )

    def test_source_link_resolves(self):
        """Sanity: the plan is findable by its procurement tag (analytic_account_id)."""
        self.assertEqual(self.plan_rec.analytic_account_id, self.proc_tag)
        self.assertEqual(self.plan_rec.budget_account_id, self.proc_ba)
        self.assertEqual(self.plan_rec.fund_analytic_id, self.fund)

    def test_aligned_procurement_line_submits(self):
        transfer = self._transfer(
            {
                "account_id": self.proc_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                "procurement_plan_analytic_id": self.proc_tag.id,
            }
        )
        res = transfer.action_submit()
        self.assertFalse(
            isinstance(res, dict) and res.get("res_model") == POPUP_MODEL
        )
        self.assertEqual(transfer.state, "submitted")
        self.assertFalse(transfer.exception_ids)

    def test_dimension_mismatch_raises_popup(self):
        transfer = self._transfer(
            {
                "account_id": self.proc_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund2.id,  # ≠ plan's fund
                "procurement_plan_analytic_id": self.proc_tag.id,
            }
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
        self.assertTrue(transfer.exception_ids)

    def test_fiscal_year_mismatch_raises_popup(self):
        """Right code + dims but a different fiscal year than the plan → popup."""
        transfer = self._transfer(
            {
                "account_id": self.proc_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                "procurement_plan_analytic_id": self.proc_tag.id,
            },
            fy=self.fy2,
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
        self.assertTrue(transfer.exception_ids)

    def test_missing_procurement_tag_raises_popup(self):
        transfer = self._transfer(
            {
                "account_id": self.proc_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                # no procurement_plan_analytic_id
            }
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
