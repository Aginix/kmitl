from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestApprovalCrossCharge(BudgetLedgerCommon):
    """ถัวจ่าย on a คำขออนุมัติ (agx_approval ADR-0011)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.third = cls.env["budget.account"].create(
            {
                "code": "LDG03",
                "name": "Ledger Not Approval",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
                "cross_chargeable": True,
            }
        )
        (cls.account | cls.other).write({"cross_chargeable": True, "approval_ok": True})
        if "is_project" in cls.account._fields:
            # The ledger fixture makes LDG01 a project code (kmitl_project); a
            # request reserving anew may not pick one.
            cls.account.is_project = False
        cls.confirmer = new_test_user(
            cls.env,
            login="cc_confirmer",
            groups="agx_approval.group_approval_budget_commit",
        )
        cls.requester = new_test_user(
            cls.env, login="cc_requester", groups="agx_approval.group_approval_user"
        )
        category = cls.env.ref("agx_approval.approval_category_5102010000")
        category.budget_account_id = False
        cls.request = cls.env["approval.request"].create(
            {
                "category_id": category.id,
                "user_id": cls.requester.id,
                "owner_id": cls.env["hr.employee"]
                .create({"name": "CC Requester", "user_id": cls.requester.id})
                .id,
                "account_fiscal_year_id": cls.fy.id,
                "budget_account_id": cls.account.id,
                "line_ids": [Command.create({"total_amount": 50_000})],
            }
        )
        dims = (cls.dept, cls.source, cls.activity, cls.fund)
        cls.request.write(
            {
                "analytic_distribution": {str(a.id): 100.0 for a in dims},
                "state": "to_commit",
            }
        )
        if cls.request._fields.get("operating_unit_id"):
            (cls.confirmer | cls.requester).write(
                {"assigned_operating_unit_ids": [(4, cls.request.operating_unit_id.id)]}
            )
        cls.env["exception.rule"].search([("model", "=", "approval.request")]).write(
            {"active": False}
        )

    def setUp(self):
        super().setUp()
        for account in (self.account, self.other, self.third):
            self._appropriate(100_000, account=account)

    def _open_dialog(self):
        action = (
            self.request.with_user(self.confirmer)
            .with_context(budget_reserve_dialog=True)
            .action_reserve_budget()
        )
        self.assertEqual(action["res_model"], "budget.commitment")
        return self.env["budget.commitment"].browse(action["res_id"])

    def _reserve_split(self, other_amount=20_000):
        slip = self._open_dialog()
        slip.with_user(self.confirmer).write(
            {
                "split_ids": [
                    Command.create(
                        {"account_id": self.other.id, "amount": other_amount}
                    )
                ]
            }
        )
        slip.with_user(self.confirmer).action_confirm_approval_reserve()
        return slip

    def _posted(self, slip):
        return sorted(
            (line.account_id.code, line.amount)
            for line in slip.line_ids
            if line.state == "posted"
        )

    def test_dialog_reserves_every_row(self):
        slip = self._open_dialog()
        self.assertEqual(slip.state, "draft")
        self.assertEqual(self.request.budget_commitment_id, slip)
        self.assertEqual(slip.amount, 50_000)
        # A draft slip reserves nothing: the button stays.
        self.assertFalse(self.request.hide_reserve_budget_button)
        slip = self._reserve_split()
        self.assertEqual(slip.state, "reserved")
        self.assertEqual(self._posted(slip), [("LDG01", 30_000), ("LDG02", 20_000)])
        self.assertEqual(self.request.state, "to_send")
        self.assertEqual(
            [line["primary"] for line in self.request._cross_charge_split_lines()],
            [True, False],
        )
        # The letter's budget table lists both codes.
        html = str(
            self.env["ir.qweb"]._render(
                "agx_approval.report_approval_request_budget", {"o": self.request}
            )
        )
        self.assertIn("LDG01", html)
        self.assertIn("LDG02", html)

    def test_cross_charge_code_must_be_approval_eligible(self):
        slip = self._open_dialog()
        self.assertIn(self.other, slip.split_account_ids)
        self.assertNotIn(self.third, slip.split_account_ids)
        slip.with_user(self.confirmer).write(
            {"split_ids": [Command.create({"account_id": self.third.id, "amount": 1})]}
        )
        self.assertIn(self.third.display_name, slip.split_warning)
        with self.assertRaises(UserError):
            slip.with_user(self.confirmer).action_confirm_approval_reserve()

    def test_primary_code_stays_selectable(self):
        slip = self._open_dialog()
        with self.assertRaises(UserError):
            slip.with_user(self.confirmer).write({"account_id": self.third.id})

    def test_recut_while_waiting_to_send(self):
        slip = self._reserve_split()
        self.assertTrue(self.request.can_adjust_cross_charge)
        row = slip.split_ids.filtered(lambda s: not s.is_primary)
        slip.with_user(self.confirmer).write(
            {"split_ids": [Command.update(row.id, {"amount": 35_000})]}
        )
        self.assertEqual(self._posted(slip), [("LDG01", 15_000), ("LDG02", 35_000)])
        # The new primary code and dimensions follow back to the request.
        slip.with_user(self.confirmer).write({"account_id": self.other.id})
        self.assertEqual(self.request.budget_account_id, self.other)
        self.assertEqual(self._posted(slip), [("LDG02", 50_000)])

    def test_locked_once_sent(self):
        slip = self._reserve_split()
        self.request.state = "sent"
        self.assertFalse(self.request.can_adjust_cross_charge)
        row = slip.split_ids.filtered(lambda s: not s.is_primary)
        with self.assertRaises(UserError):
            slip.with_user(self.confirmer).write(
                {"split_ids": [Command.update(row.id, {"amount": 35_000})]}
            )
        # A return not from e-Saraban (e.g. from a disbursement) stays locked.
        self.request.state = "returned"
        self.assertFalse(self.request.can_adjust_cross_charge)

    def test_requester_cannot_write_the_slip(self):
        slip = self._open_dialog()
        with self.assertRaises(UserError):
            slip.with_user(self.requester).write(
                {
                    "split_ids": [
                        Command.create({"account_id": self.other.id, "amount": 1})
                    ]
                }
            )

    def test_pull_back_revives_the_slip(self):
        slip = self._reserve_split()
        self.request.action_draft()
        self.assertEqual(slip.state, "cancel")
        self.request.state = "to_commit"
        self.assertEqual(self._open_dialog(), slip)
        self.assertEqual(slip.state, "draft")
        self.assertEqual(
            {(s.account_id, s.amount) for s in slip.split_ids},
            {(self.account, 30_000), (self.other, 20_000)},
        )
