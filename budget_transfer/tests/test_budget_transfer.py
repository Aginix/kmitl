from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetTransfer(TransactionCase):
    """Budget transfer as a 1:1 delegated budget.move with folded move lines
    (ADR-0013). Exercises the delegation, the FROM/TO authoring on
    ``budget.move.line``, availability via the control-node engine, the
    source-locked / four-dim / tag policy (ADR-0009/0012), and the workflow
    guards."""

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

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
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
            # The header department defaults onto each line via the view context;
            # in tests there is no view, so stamp it explicitly.
            vals.setdefault("department_analytic_id", self.dept.id)
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

    def _balanced(self):
        return {
            "from_lines": [
                {
                    "account_id": self.src.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            "to_lines": [
                {
                    "account_id": self.dst.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        }

    # ------------------------------------------------------------------
    # delegation
    # ------------------------------------------------------------------
    def test_transfer_owns_a_delegated_entry_move(self):
        transfer = self._transfer(**self._balanced())
        self.assertTrue(transfer.move_id, "a budget.move is created up front")
        self.assertEqual(transfer.move_id.move_type, "entry")
        self.assertEqual(transfer.move_id.state, "draft")
        # Header fields resolve through delegation.
        self.assertEqual(transfer.company_id, transfer.move_id.company_id)
        self.assertEqual(transfer.date, transfer.move_id.date)
        # The lines are the move's own lines.
        self.assertEqual(transfer.line_ids, transfer.move_id.line_ids)
        self.assertEqual(len(transfer.from_line_ids), 1)
        self.assertEqual(len(transfer.to_line_ids), 1)
        # Reverse link back from the move.
        self.assertEqual(transfer.move_id.transfer_ids, transfer)
        self.assertTrue(transfer.move_id.is_transfer)

    def test_amount_sums_from_lines(self):
        transfer = self._transfer(**self._balanced())
        self.assertEqual(transfer.amount, 1000)

    # ------------------------------------------------------------------
    # dimensions / availability
    # ------------------------------------------------------------------
    def test_source_locked_to_header(self):
        transfer = self._transfer(**self._balanced())
        for line in transfer.line_ids:
            self.assertEqual(line.source_analytic_id, self.source)

    def test_from_availability_reads_control_node_engine(self):
        self._appropriate(self.src, 100_000)
        transfer = self._transfer(
            from_lines=[
                {
                    "account_id": self.src.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
            to_lines=[
                {
                    "account_id": self.dst.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        from_line = transfer.from_line_ids
        engine = self.controller.get_available(
            self.src,
            from_line._transfer_distribution(),
            self.fy.id,
            self.env.company.id,
        )
        self.assertEqual(from_line.available_budget, engine)
        self.assertEqual(from_line.available_budget, 100_000)
        self.assertTrue(from_line.budget_sufficient)

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def test_post_drives_the_delegated_move_balanced(self):
        self._appropriate(self.src, 100_000)
        transfer = self._transfer(**self._balanced())
        transfer.action_submit()
        transfer.action_approve()
        transfer.action_post()
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(transfer.move_id.state, "posted")
        from_line = transfer.from_line_ids
        to_line = transfer.to_line_ids
        self.assertEqual((from_line.credit, from_line.balance), (1000, -1000))
        self.assertEqual((to_line.debit, to_line.balance), (1000, 1000))
        # Balanced entry move.
        self.assertAlmostEqual(sum(transfer.line_ids.mapped("balance")), 0.0, places=2)

    def test_admin_can_approve_own_transfer(self):
        self._appropriate(self.src, 100_000)
        transfer = self._transfer(**self._balanced())
        transfer.action_submit()
        transfer.action_approve()  # admin == requestor, but admin bypasses SoD
        self.assertEqual(transfer.state, "approved")

    def test_non_admin_cannot_approve_own_transfer(self):
        self._appropriate(self.src, 100_000)
        mgr = self.env["res.users"].create(
            {
                "name": "Budget Mgr",
                "login": "budget_mgr_tr",
                "groups_id": [
                    Command.link(self.env.ref("budget.group_budget_manager").id)
                ],
            }
        )
        transfer = self._transfer(**self._balanced())
        transfer.user_id = mgr
        transfer.with_user(mgr).action_submit()
        with self.assertRaises(UserError):
            transfer.with_user(mgr).action_approve()

    def test_reset_blocked_on_posted(self):
        self._appropriate(self.src, 100_000)
        transfer = self._transfer(**self._balanced())
        transfer.action_submit()
        transfer.action_approve()
        transfer.action_post()
        with self.assertRaises(UserError):
            transfer.action_reset_to_draft()

    def test_core_dims_required_on_submit(self):
        # A FROM line missing its fund fails the four-dim check at submit.
        transfer = self._transfer(
            from_lines=[
                {
                    "account_id": self.src.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                }
            ],
            to_lines=[
                {
                    "account_id": self.dst.id,
                    "amount": 1000,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            ],
        )
        with self.assertRaises(ValidationError):
            transfer.action_submit()

    # ------------------------------------------------------------------
    # Pool-Tag policy (ADR-0009 / ADR-0012)
    # ------------------------------------------------------------------
    def test_supplementary_dims_mutually_exclusive(self):
        with self.assertRaises(ValidationError):
            self._transfer(
                from_lines=[
                    {
                        "account_id": self.src.id,
                        "amount": 1000,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                        "kmitl_project_analytic_id": self.proj.id,
                        "procurement_plan_analytic_id": self.proc.id,
                    }
                ],
                to_lines=[
                    {
                        "account_id": self.dst.id,
                        "amount": 1000,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                    }
                ],
            )

    def test_project_tag_on_non_project_account_raises(self):
        # self.src is a plain expense account (not is_project).
        with self.assertRaises(ValidationError):
            self._transfer(
                from_lines=[
                    {
                        "account_id": self.src.id,
                        "amount": 1000,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                        "kmitl_project_analytic_id": self.proj.id,
                    }
                ],
                to_lines=[
                    {
                        "account_id": self.dst.id,
                        "amount": 1000,
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                    }
                ],
            )
