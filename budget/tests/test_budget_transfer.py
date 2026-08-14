from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetTransfer(TransactionCase):
    """Budget transfer foundation (ADR-0009): 5-dimension lines, availability via
    the control-node engine, source-locked policy, and the cleanup guards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-TR",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "TR_SRC", "name": "Transfer Src", "budget_type": "expense"}
        )
        cls.dst = BA.create(
            {"code": "TR_DST", "name": "Transfer Dst", "budget_type": "expense"}
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

        cls.dept = acc("Dept", "TR_DEPT", "departments", "Departments")
        cls.source = acc("Source", "TR_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "TR_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "TR_FUND", "funds", "Funds")
        cls.proj = acc("Project", "TR_PROJ", "kmitl_project", "Project")
        cls.proc = acc("Proc", "TR_PROC", "procurement_plan", "Procurement Plan")
        cls.controller = env["budget.controller"]

    # --- helpers ---

    def _appropriate(self, account, amount, activity=None, fund=None):
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
                            "account_id": account.id,
                            "balance": amount,
                            "activity_analytic_id": (activity or self.activity).id,
                            "fund_analytic_id": (fund or self.fund).id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _transfer(self, from_lines, to_lines):
        def line(vals, direction):
            vals = dict(vals)
            vals["transfer_direction"] = direction
            return Command.create(vals)

        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "reason": "test transfer",
                "line_ids": [line(v, "from") for v in from_lines]
                + [line(v, "to") for v in to_lines],
            }
        )

    # --- tests ---

    def test_line_distribution_carries_five_dimensions(self):
        """A FROM line driven by its convenience fields stores all dims in the
        JSON distribution, including the 5th (procurement_plan), plus the header
        source."""
        transfer = self._transfer(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                    "procurement_plan_analytic_id": self.proc.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        from_line = transfer.line_ids.filtered(
            lambda l: l.transfer_direction == "from"
        )
        dist_ids = {int(k) for k in (from_line.analytic_distribution or {})}
        # all five active dims present: activity, fund, dept (header), source
        # (header), procurement_plan
        self.assertIn(self.activity.id, dist_ids)
        self.assertIn(self.fund.id, dist_ids)
        self.assertIn(self.dept.id, dist_ids)
        self.assertIn(self.source.id, dist_ids)
        self.assertIn(self.proc.id, dist_ids)

    def test_from_availability_reads_control_node_engine(self):
        """A FROM line's available_budget equals the engine's get_available for
        the line's own distribution."""
        self._appropriate(self.src, 100_000)
        transfer = self._transfer(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 30_000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 30_000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        from_line = transfer.line_ids.filtered(
            lambda l: l.transfer_direction == "from"
        )
        engine = self.controller.get_available(
            self.src.id, from_line.analytic_distribution or {}, self.fy.id
        )
        self.assertEqual(from_line.available_budget, engine)
        self.assertEqual(from_line.available_budget, 100_000)
        self.assertTrue(from_line.budget_sufficient)

    def test_source_locked_to_header(self):
        """Every line's source mirrors the header source (no cross-source)."""
        transfer = self._transfer(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        for line in transfer.line_ids:
            self.assertEqual(line.source_analytic_id, self.source)

    def _balanced_lines(self):
        return dict(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )

    def test_admin_can_approve_own_transfer(self):
        """An admin may submit + approve a transfer they requested (on behalf)."""
        self._appropriate(self.src, 100_000)
        self.env.user.groups_id = [
            Command.link(self.env.ref("budget.group_budget_manager").id)
        ]
        transfer = self._transfer(**self._balanced_lines())
        transfer.action_submit()
        transfer.action_approve()  # admin == requestor, but admin bypasses SoD
        self.assertEqual(transfer.state, "approved")

    def test_non_admin_cannot_approve_own_transfer(self):
        """Segregation of duties: a non-admin requestor cannot approve their own."""
        mgr = self.env["res.users"].create(
            {
                "name": "Budget Mgr",
                "login": "tr_budget_mgr",
                "groups_id": [
                    Command.link(self.env.ref("budget.group_budget_manager").id)
                ],
            }
        )
        transfer = self._transfer(**self._balanced_lines())
        transfer.user_id = mgr
        transfer.state = "submitted"
        with self.assertRaises(UserError):
            transfer.with_user(mgr).action_approve()

    def test_reset_blocked_on_posted(self):
        """A posted transfer cannot be reset to draft."""
        transfer = self._transfer(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 500,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        transfer.state = "posted"
        with self.assertRaises(UserError):
            transfer.action_reset_to_draft()

    # --- dimension rules ---

    def test_supplementary_dims_mutually_exclusive(self):
        """A line may carry procurement_plan XOR kmitl_project, never both."""
        with self.assertRaises(ValidationError):
            self._transfer(
                from_lines=[
                    {
                        "budget_account_id": self.src.id,
                        "amount": 100,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                        "procurement_plan_analytic_id": self.proc.id,
                        "kmitl_project_analytic_id": self.proj.id,
                    }
                ],
                to_lines=[
                    {
                        "budget_account_id": self.dst.id,
                        "amount": 100,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                    }
                ],
            )

    def test_core_dims_required_on_submit(self):
        """Submitting requires all four core dims (dept/source/activity/fund) on
        every line — here the FROM line omits activity."""
        transfer = self._transfer(
            from_lines=[
                {
                    "budget_account_id": self.src.id,
                    "amount": 100,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "budget_account_id": self.dst.id,
                    "amount": 100,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        with self.assertRaises(ValidationError):
            transfer.action_submit()
