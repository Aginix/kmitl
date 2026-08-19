from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged

POPUP_MODEL = "budget.transfer.exception.confirm"


@tagged("post_install", "-at_install")
class TestBudgetTransferExceptionKmitlProject(TransactionCase):
    """On ยืนยัน (action_submit), a transfer line whose budget code is a project
    code (``is_project``) must match its ``kmitl.project`` source — same budget
    code, same fiscal year, and same four core dimensions — else the
    base.exception review popup is raised instead of proceeding to ``submitted``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-TREXC",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        # A different fiscal year to exercise the year mismatch.
        cls.fy2 = env["account.fiscal.year"].create(
            {
                "name": "FY-TREXC-2",
                "date_from": date(2026, 10, 1),
                "date_to": date(2027, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        # A plain drawing code funds the FROM side (availability checked there).
        cls.src = BA.create(
            {"code": "TRX_SRC", "name": "Src", "budget_type": "expense"}
        )
        # A project code on the TO side is what the exception validates.
        cls.proj_ba = BA.create(
            {
                "code": "TRX_PROJBA",
                "name": "Project BA",
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

        cls.dept = acc("Dept", "TRX_DEPT", "departments", "Departments")
        cls.source = acc("Source", "TRX_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "TRX_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "TRX_FUND", "funds", "Funds")
        cls.fund2 = acc("Fund2", "TRX_FUND2", "funds", "Funds")
        cls.proj_tag = acc("ProjTag", "TRX_PROJ", "kmitl_project", "Project")

        # The source-of-truth project the transfer must agree with.
        cls.project = env["kmitl.project"].create(
            {
                "name": "Test Project",
                "project_type": "project",
                "account_fiscal_year_id": cls.fy.id,
                "budget_account_id": cls.proj_ba.id,
                "analytic_account_id": cls.proj_tag.id,
                "activity_analytic_id": cls.activity.id,
                "department_analytic_id": cls.dept.id,
                "fund_analytic_id": cls.fund.id,
                "source_analytic_id": cls.source.id,
            }
        )

        # Fund the FROM side so availability passes and submit reaches our check.
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
        """A balanced transfer: FROM the plain code, TO the project code."""
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

    def test_aligned_project_line_submits(self):
        """Matching code + dims → submit proceeds, no exception."""
        transfer = self._transfer(
            {
                "account_id": self.proj_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                "kmitl_project_analytic_id": self.proj_tag.id,
            }
        )
        res = transfer.action_submit()
        self.assertFalse(
            isinstance(res, dict) and res.get("res_model") == POPUP_MODEL,
            "should not pop the wizard",
        )
        self.assertEqual(transfer.state, "submitted")
        self.assertFalse(transfer.exception_ids)

    def test_dimension_mismatch_raises_popup(self):
        """A wrong core dimension (fund) → review popup, stays draft."""
        transfer = self._transfer(
            {
                "account_id": self.proj_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund2.id,  # ≠ project's fund
                "kmitl_project_analytic_id": self.proj_tag.id,
            }
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
        self.assertTrue(transfer.exception_ids)

    def test_fiscal_year_mismatch_raises_popup(self):
        """Right code + dims but a different fiscal year than the project → popup."""
        transfer = self._transfer(
            {
                "account_id": self.proj_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                "kmitl_project_analytic_id": self.proj_tag.id,
            },
            fy=self.fy2,
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
        self.assertTrue(transfer.exception_ids)

    def test_missing_project_tag_raises_popup(self):
        """Project code without its project dimension tag → review popup."""
        transfer = self._transfer(
            {
                "account_id": self.proj_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund.id,
                # no kmitl_project_analytic_id
            }
        )
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")

    def test_ignore_blocking_exception_still_blocks(self):
        """The rule ships blocking → ignoring via the wizard cannot bypass it."""
        transfer = self._transfer(
            {
                "account_id": self.proj_ba.id,
                "activity_analytic_id": self.activity.id,
                "fund_analytic_id": self.fund2.id,
                "kmitl_project_analytic_id": self.proj_tag.id,
            }
        )
        transfer.action_submit()  # detect + populate exception_ids
        wizard = (
            self.env[POPUP_MODEL]
            .with_context(
                active_model="budget.transfer",
                active_id=transfer.id,
                active_ids=transfer.ids,
            )
            .create({"ignore": True})
        )
        wizard.action_confirm()
        self.assertEqual(transfer.state, "draft")
        self.assertFalse(transfer.ignore_exception)
