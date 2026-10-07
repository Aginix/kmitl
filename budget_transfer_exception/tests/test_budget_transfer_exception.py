from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

POPUP_MODEL = "budget.transfer.exception.confirm"


@tagged("post_install", "-at_install")
class TestBudgetTransferException(TransactionCase):
    """The transfer's business-policy checks (4 core dimensions, budget
    availability) are exception.rule records: active → ยืนยัน pops the review
    wizard (and approve re-checks); archived → the check is switched off."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-TRE",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "TRE_SRC", "name": "Src", "budget_type": "expense"}
        )
        cls.dst = BA.create(
            {"code": "TRE_DST", "name": "Dst", "budget_type": "expense"}
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": name, "code": code, "plan_id": plan.id})

        cls.dept = acc("Dept", "TRE_DEPT", "departments")
        cls.source = acc("Source", "TRE_SRCM", "sources")
        cls.activity = acc("Activity", "TRE_ACT", "activities")
        cls.fund = acc("Fund", "TRE_FUND", "funds")
        cls.proj = acc("Project", "TRE_PROJ", "kmitl_project")

        cls.rule_dims = env.ref(
            "budget_transfer_exception.budget_transfer_excep_core_dimensions"
        )
        cls.rule_avail = env.ref(
            "budget_transfer_exception.budget_transfer_excep_budget_availability"
        )
        cls.rule_tag_account = env.ref(
            "budget_transfer_exception.budget_transfer_excep_tag_account_mismatch"
        )
        cls.rule_duplicate = env.ref(
            "budget_transfer_exception.budget_transfer_excep_duplicate_lines"
        )

    def _appropriate(self, amount):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.src.id,
                            "balance": amount,
                            "activity_analytic_id": self.activity.id,
                            "fund_analytic_id": self.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()

    def _transfer(self, from_fund=True):
        def line(account, direction, fund):
            return Command.create(
                {
                    "transfer_direction": direction,
                    "account_id": account.id,
                    "amount": 1000,
                    "department_analytic_id": self.dept.id,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": fund.id,
                }
            )

        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "reason": "test",
                "line_ids": [
                    line(
                        self.src, "from", self.fund if from_fund else self.fund.browse()
                    ),
                    line(self.dst, "to", self.fund),
                ],
            }
        )

    def _assert_popup(self, transfer, rule):
        res = transfer.action_submit()
        self.assertEqual(res.get("res_model"), POPUP_MODEL)
        self.assertEqual(transfer.state, "draft")
        self.assertIn(rule, transfer.exception_ids)

    def test_missing_core_dimension_raises_popup(self):
        self._appropriate(100_000)
        self._assert_popup(self._transfer(from_fund=False), self.rule_dims)

    def test_core_dimension_rule_off_allows_submit(self):
        self._appropriate(100_000)
        self.rule_dims.active = False
        transfer = self._transfer(from_fund=False)
        transfer.action_submit()
        self.assertEqual(transfer.state, "submitted")

    def test_insufficient_budget_raises_popup(self):
        self._assert_popup(self._transfer(), self.rule_avail)

    def test_availability_rule_off_allows_submit_and_post(self):
        self.rule_avail.active = False
        transfer = self._transfer()
        transfer.action_submit()
        transfer.action_approve()
        self.assertEqual(transfer.state, "posted")

    def test_approve_rechecks_exceptions(self):
        self.rule_avail.active = False
        transfer = self._transfer()
        transfer.action_submit()
        self.rule_avail.active = True
        with self.assertRaises(ValidationError):
            transfer.action_approve()
        self.assertEqual(transfer.state, "submitted")

    def _line(self, account, direction, amount, **extra):
        return Command.create(
            dict(
                transfer_direction=direction,
                account_id=account.id,
                amount=amount,
                department_analytic_id=self.dept.id,
                activity_analytic_id=self.activity.id,
                fund_analytic_id=self.fund.id,
                **extra,
            )
        )

    def _transfer_lines(self, lines):
        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "reason": "test",
                "line_ids": lines,
            }
        )

    def _duplicate_transfer(self):
        return self._transfer_lines(
            [
                self._line(self.src, "from", 500),
                self._line(self.src, "from", 500),
                self._line(self.dst, "to", 1000),
            ]
        )

    def _tag_mismatch_transfer(self):
        # self.dst is a plain expense account — a project tag doesn't belong.
        return self._transfer_lines(
            [
                self._line(self.src, "from", 1000),
                self._line(
                    self.dst, "to", 1000, kmitl_project_analytic_id=self.proj.id
                ),
            ]
        )

    def test_duplicate_lines_raise_popup(self):
        self._appropriate(100_000)
        self._assert_popup(self._duplicate_transfer(), self.rule_duplicate)

    def test_duplicate_rule_off_allows_submit(self):
        self._appropriate(100_000)
        self.rule_duplicate.active = False
        transfer = self._duplicate_transfer()
        transfer.action_submit()
        self.assertEqual(transfer.state, "submitted")

    def test_tag_account_mismatch_raises_popup(self):
        self._appropriate(100_000)
        self._assert_popup(self._tag_mismatch_transfer(), self.rule_tag_account)

    def test_tag_account_rule_off_allows_submit(self):
        self._appropriate(100_000)
        self.rule_tag_account.active = False
        transfer = self._tag_mismatch_transfer()
        transfer.action_submit()
        self.assertEqual(transfer.state, "submitted")
