import json
from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestFloatingAllocation(TransactionCase):
    """จัดสรรงบประมาณ (งบลอย) — Direct Floating Allocation (ADR-0009): the wizard
    moves the floating pool covering the project's coordinate into the project's
    dimension through a budget.transfer posted at once."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        # kmitl_demo enables it; the wizard and the reserve check must see the cap.
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)

        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPFA",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.ou = env.ref("operating_unit.main_operating_unit")
        cls.budget_account = env["budget.account"].create(
            {
                "code": "KPFA_PROJBA",
                "name": "KPFA Project BA",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code, parent=None):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            vals = {"name": name, "code": code, "plan_id": plan.id}
            if parent:
                vals["parent_id"] = parent.id
            return AA.create(vals)

        cls.dept = acc("Dept", "KPFA_DEPT", "departments")
        cls.source = acc("Source", "KPFA_SRC", "sources")
        cls.fund = acc("Fund", "KPFA_FUND", "funds")
        cls.fund_other = acc("Fund other", "KPFA_FUND2", "funds")
        cls.activity = acc("Activity", "KPFA_ACT", "activities")
        cls.activity_parent = acc("Main activity", "KPFA_ACTP", "activities")
        cls.activity_child = acc(
            "Sub activity", "KPFA_ACTC", "activities", cls.activity_parent
        )

        cls.budget_user = new_test_user(
            env,
            login="kpfa_budget_user",
            name="เจ้าหน้าที่แผนงาน",
            groups="base.group_user,budget.group_budget_user,"
            "kmitl_project.group_kmitl_project_user_all",
            operating_unit_ids=[Command.set(cls.ou.ids)],
            default_operating_unit_id=cls.ou.id,
        )
        cls.plain_user = new_test_user(
            env,
            login="kpfa_plain_user",
            groups="base.group_user,kmitl_project.group_kmitl_project_user_all",
            operating_unit_ids=[Command.set(cls.ou.ids)],
            default_operating_unit_id=cls.ou.id,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _appropriate(self, amount, activity=None, fund=None):
        line = {
            "account_id": self.budget_account.id,
            "balance": amount,
            "activity_analytic_id": (activity or self.activity).id,
            "fund_analytic_id": (fund or self.fund).id,
        }
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": [Command.create(line)],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _project(self, activity=None, fund=None):
        project = self.env["kmitl.project"].create(
            {
                "name": "KPFA Project",
                "project_type": "project",
                "operating_unit_id": self.ou.id,
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.budget_account.id,
                "activity_analytic_id": (activity or self.activity).id,
                "department_analytic_id": self.dept.id,
                "fund_analytic_id": (fund or self.fund).id,
                "source_analytic_id": self.source.id,
            }
        )
        project.action_confirm()  # ส่งเข้าแผน: mints the analytic
        return project

    def _wizard(self, project, user=None):
        Wizard = self.env["kmitl.project.floating.allocation"]
        if user:
            Wizard = Wizard.with_user(user)
        return Wizard.create({"project_id": project.id})

    def _allocate(self, project, amount, user=None):
        wizard = self._wizard(project, user)
        wizard.amount = amount
        wizard.action_next()
        wizard.action_confirm()
        return wizard

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------
    def test_budget_user_allocates_and_posts_at_once(self):
        self._appropriate(100000)
        project = self._project()
        wizard = self._wizard(project, self.budget_user)
        self.assertTrue(wizard.pool_found)
        self.assertEqual(wizard.floating_available, 100000)

        wizard.amount = 30000
        wizard.action_next()
        self.assertEqual(wizard.step, "review")
        wizard.action_confirm()

        transfer = wizard.transfer_id
        self.assertEqual(wizard.step, "done")
        self.assertEqual(transfer.state, "posted")
        self.assertTrue(transfer.is_floating_allocation)
        self.assertEqual(transfer.kmitl_project_id, project)
        self.assertEqual(transfer.approver_id, self.budget_user)
        from_line = transfer.line_ids.filtered(
            lambda line: line.transfer_direction == "from"
        )
        to_line = transfer.line_ids.filtered(
            lambda line: line.transfer_direction == "to"
        )
        self.assertFalse(from_line.kmitl_project_analytic_id)
        self.assertEqual(to_line.kmitl_project_analytic_id, project.analytic_account_id)
        self.assertEqual(project.budget_amount, 30000)
        wizard.invalidate_recordset(["floating_available"])
        self.assertEqual(wizard.floating_available, 70000)

    def test_amount_above_floating_available_raises(self):
        self._appropriate(10000)
        wizard = self._wizard(self._project())
        wizard.amount = 10000.01
        with self.assertRaises(UserError):
            wizard.action_next()

    def test_no_covering_pool(self):
        self._appropriate(10000, fund=self.fund_other)
        wizard = self._wizard(self._project())
        self.assertFalse(wizard.pool_found)
        wizard.amount = 100
        with self.assertRaises(UserError):
            wizard.action_next()

    def test_non_budget_user_denied(self):
        self._appropriate(10000)
        project = self._project()
        with self.assertRaises(UserError):
            project.with_user(self.plain_user).action_open_floating_allocation()

    def test_draft_project_denied(self):
        project = self.env["kmitl.project"].create(
            {
                "name": "KPFA Draft",
                "project_type": "project",
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.budget_account.id,
            }
        )
        with self.assertRaises(UserError):
            project.action_open_floating_allocation()

    def test_pool_at_parent_activity_draws_from_parent(self):
        self._appropriate(50000, activity=self.activity_parent)
        project = self._project(activity=self.activity_child)
        wizard = self._allocate(project, 20000)
        from_line = wizard.transfer_id.line_ids.filtered(
            lambda line: line.transfer_direction == "from"
        )
        self.assertEqual(from_line.activity_analytic_id, self.activity_parent)
        self.assertEqual(project.budget_amount, 20000)

    def test_reserved_commitment_follows_top_up(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        project.action_approve()  # reserves (kmitl_project ADR-0010)
        self.assertEqual(project.state, "in_progress")

        self._allocate(project, 20000)
        active = project.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertEqual(project.budget_amount, 50000)
        self.assertEqual(active.amount, 50000)

    def test_dimension_rows_follow_the_display_order(self):
        self._appropriate(10000)
        project = self._project()
        wizard = self._wizard(project)
        self.assertEqual(
            [row["key"] for row in json.loads(wizard.pool_dims)],
            [
                "source_analytic_id",
                "department_analytic_id",
                "fund_analytic_id",
                "activity_analytic_id",
                "account_id",
            ],
        )
        to_rows = json.loads(wizard.project_dims)
        self.assertEqual(to_rows[-1]["key"], "kmitl_project_analytic_id")
        self.assertEqual(to_rows[4]["code"], self.budget_account.code)

    def test_used_up_pool_raises(self):
        """A pool whose availability is fully reserved still resolves (its
        appropriation stands) but has nothing left to move."""
        self._appropriate(10000)
        project = self._project()
        Commitment = self.env["budget.commitment"]
        vals = {
            "title": "KPFA reservation",
            "account_id": self.budget_account.id,
            "amount": 10000,
            "analytic_distribution": {
                str(a.id): 100
                for a in (self.dept, self.source, self.fund, self.activity)
            },
            "account_fiscal_year_id": self.fy.id,
        }
        if "operating_unit_id" in Commitment._fields:
            vals["operating_unit_id"] = self.ou.id
        Commitment.create(vals).action_reserve()
        wizard = self._wizard(project)
        self.assertTrue(wizard.pool_found)
        self.assertEqual(wizard.floating_available, 0)
        wizard.amount = 1
        with self.assertRaises(UserError):
            wizard.action_next()

    # ------------------------------------------------------------------
    # โอนคืนงบลอย — Floating Return (kmitl_project ADR-0011)
    # ------------------------------------------------------------------
    def _return_wizard(self, project, user=None):
        Wizard = self.env["kmitl.project.floating.return"]
        if user:
            Wizard = Wizard.with_user(user)
        return Wizard.create({"project_id": project.id})

    def test_return_goes_back_to_the_project_floating_pool(self):
        """The money goes back as Floating Budget at the project's own รหัสงบ +
        four dimensions — not to wherever a transfer brought it from."""
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)

        wizard = self._return_wizard(project, self.budget_user)
        self.assertTrue(wizard.pool_found)
        self.assertEqual(wizard.floating_available, 30000)
        wizard.amount = 10000
        wizard.action_next()
        wizard.action_confirm()

        transfer = wizard.transfer_id
        self.assertEqual(transfer.state, "posted")
        self.assertTrue(transfer.is_floating_return)
        self.assertFalse(transfer.is_floating_allocation)
        to_line = transfer.line_ids.filtered(
            lambda line: line.transfer_direction == "to"
        )
        self.assertEqual(to_line.account_id, project.budget_account_id)
        self.assertEqual(
            set(to_line.analytic_distribution),
            set(project.analytic_distribution) - {str(project.analytic_account_id.id)},
        )
        self.assertEqual(project.budget_amount, 20000)
        self.assertEqual(self._return_wizard(project).floating_available, 20000)

    def test_return_to_parent_pool_never_nests(self):
        """Money drawn from a pool at the parent activity goes back to that
        pool; a new pool at the project's child activity would nest with it
        (budget ADR-0016)."""
        self._appropriate(50000, activity=self.activity_parent)
        project = self._project(activity=self.activity_child)
        self._allocate(project, 20000)
        wizard = self._return_wizard(project)
        wizard.amount = 20000
        wizard.action_next()
        wizard.action_confirm()
        to_line = wizard.transfer_id.line_ids.filtered(
            lambda line: line.transfer_direction == "to"
        )
        self.assertEqual(to_line.activity_analytic_id, self.activity_parent)
        self.assertEqual(project.budget_amount, 0)

    def test_return_releases_the_reservation(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        project.action_approve()
        commitment = project.budget_commitment_ids
        self.assertEqual(commitment.available_to_obligate, 30000)

        wizard = self._return_wizard(project)
        wizard.amount = 30000
        wizard.action_next()
        wizard.action_confirm()
        self.assertEqual(project.budget_amount, 0)
        self.assertEqual(commitment.available_to_obligate, 0)
        self.assertFalse(project._get_held_money_reasons())

    def test_return_cap_drops_by_obligated_and_consumed(self):
        """The unobligated reservation comes out with the return, but what is
        obligated or consumed stays at the project."""
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        project.action_approve()
        commitment = project.budget_commitment_ids
        self.assertEqual(self._return_wizard(project).floating_available, 30000)
        commitment._post_budget_event("obligate", 10000)
        self.assertEqual(self._return_wizard(project).floating_available, 20000)
        commitment._post_budget_event("consume", 4000)
        self.assertEqual(self._return_wizard(project).floating_available, 20000)

    def test_return_above_returnable_raises(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        wizard = self._return_wizard(project)
        wizard.amount = 30000.01
        with self.assertRaises(UserError):
            wizard.action_next()

    def test_return_blocked_while_budget_confirmed(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        self.assertEqual(project.state, "to_send")
        with self.assertRaises(UserError):
            project.action_open_floating_return()

    def test_return_denied_to_non_budget_user(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        with self.assertRaises(UserError):
            project.with_user(self.plain_user).action_open_floating_return()

    def test_pending_transfer_holds_money(self):
        """A submitted transfer naming the project's dimension that has not
        posted yet keeps the project from being retargeted or deleted."""
        self._appropriate(100000)
        project = self._project()
        wizard = self._wizard(project)
        wizard.amount = 1000
        transfer = self.env["budget.transfer"].create(wizard._prepare_transfer_vals())
        self.assertFalse(project._has_pending_project_transfer())
        transfer.action_submit()
        self.assertTrue(project._has_pending_project_transfer())
        with self.assertRaises(UserError):
            project.unlink()

    def test_draft_transfer_does_not_block_delete(self):
        """A draft transfer has not been sent, so it holds no money: the
        project is soft-deleted (the draft is its Ledger Footprint)."""
        self._appropriate(100000)
        project = self._project()
        wizard = self._wizard(project)
        wizard.amount = 1000
        self.env["budget.transfer"].create(wizard._prepare_transfer_vals())
        project.unlink()
        self.assertEqual(project.state, "cancel")
        self.assertFalse(project.active)

    def test_full_return_then_delete_soft_deletes(self):
        self._appropriate(100000)
        project = self._project()
        self._allocate(project, 30000)
        wizard = self._return_wizard(project)
        wizard.action_next()
        wizard.action_confirm()
        project.unlink()
        self.assertEqual(project.state, "cancel")
        self.assertFalse(project.active)
        self.assertFalse(project.analytic_account_id.active)
