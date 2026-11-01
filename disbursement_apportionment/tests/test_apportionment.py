# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestApportionment(BudgetLedgerCommon):
    """A request with an apportionment (ปันส่วน, ADR-0009) consumes its payee
    lines directly from the pool and, in the same act, posts a budget transfer
    of the apportioned share to its apportionment lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Project Head",
                "bank_ids": [(0, 0, {"acc_number": "1234567890"})],
            }
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.dept_rector = cls.env["account.analytic.account"].create(
            {
                "name": "Rector Office",
                "code": "LDG_DEPT89",
                "plan_id": cls.dept.plan_id.id,
            }
        )
        cls.rector = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Apportion Rector",
                    "login": "ap_rector",
                    "email": "ap_rector@example.com",
                    "groups_id": [
                        Command.link(
                            cls.env.ref(
                                "disbursement.group_disbursement_rector_delegate"
                            ).id
                        )
                    ],
                }
            )
        )

    def _destination(self, amount, dept=None):
        return Command.create(
            {
                "budget_account_id": self.other.id,
                "amount": amount,
                "analytic_distribution": {
                    str((dept or self.dept_rector).id): 100.0,
                    str(self.fund.id): 100.0,
                    str(self.activity.id): 100.0,
                },
            }
        )

    def _request(self, paid, apportioned):
        dr = self.env["disbursement.request"].create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "is_apportioned": True,
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.account.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.expense_account.id,
                            "name": "ค่าตอบแทนหัวหน้าโครงการ",
                            "amount": paid,
                            "partner_id": self.partner.id,
                        }
                    )
                ],
                "apportionment_line_ids": [self._destination(a) for a in apportioned],
            }
        )
        dr.analytic_distribution = self._distribution()
        return dr

    def _to_signed(self, dr):
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")
        with patch.object(type(dr), "_on_signed"):
            dr.action_sign()

    def test_consume_payees_and_transfer_apportionment(self):
        self._appropriate(1_000_000)
        dr = self._request(900_000, [60_000, 40_000])
        self.assertEqual(dr.apportionment_amount, 100_000)
        self.assertEqual(dr.budget_total_amount, 1_000_000)
        self._to_signed(dr)
        # The Rector delegate holds no budget right at all.
        dr.with_user(self.rector).action_consume_budget()

        self.assertEqual(dr.budget_direct_move_id.state, "posted")
        self.assertEqual(dr.budget_consumed_amount, 900_000)
        transfer = dr.apportionment_transfer_id
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(transfer.disbursement_request_id, dr)
        from_lines = transfer.line_ids.filtered(
            lambda line: line.transfer_direction == "from"
        )
        to_lines = transfer.line_ids.filtered(
            lambda line: line.transfer_direction == "to"
        )
        self.assertEqual(sum(from_lines.mapped("amount")), 100_000)
        self.assertEqual(from_lines.account_id, self.account)
        self.assertEqual(sorted(to_lines.mapped("amount")), [40_000, 60_000])
        self.assertEqual(to_lines.account_id, self.other)
        self.assertEqual(to_lines.department_analytic_id, self.dept_rector)
        self.assertEqual(to_lines.source_analytic_id, self.source)
        # The source loses exactly the income.
        self.assertEqual(self._available(), 0.0)

        # Idempotent after a divert back.
        dr._action_approve_budget()
        self.assertEqual(dr.apportionment_transfer_id, transfer)
        self.assertEqual(self._available(), 0.0)

    def test_submit_blocked_when_pool_short_of_budget_total(self):
        # Enough for the payees, not for the payees and the apportionment.
        self._appropriate(950_000)
        dr = self._request(900_000, [100_000])
        self.assertTrue(dr._direct_claim_budget_shortfall())
        dr.action_submit()
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref(
                "disbursement_apportionment.excep_disbursement_apportionment_available"
            ),
            dr.exception_ids,
        )

    def test_no_reservation(self):
        self._appropriate(1_000_000)
        dr = self._request(900_000, [100_000])
        dr.budget_commitment_id = self._reserve(500_000)
        with self.assertRaises(UserError):
            dr._action_approve_budget()

    def test_cancel_keeps_the_transfer(self):
        self._appropriate(1_000_000)
        dr = self._request(900_000, [100_000])
        self._to_signed(dr)
        dr.action_consume_budget()
        transfer = dr.apportionment_transfer_id
        dr.action_cancel()
        self.assertEqual(dr.budget_direct_move_id.state, "cancel")
        self.assertEqual(transfer.state, "posted")
        # The payees' 900,000 is back; the apportioned 100,000 stays moved.
        self.assertEqual(self._available(), 900_000)

    def test_right_required_to_tick(self):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Plain Requester",
                    "login": "ap_plain",
                    "email": "ap_plain@example.com",
                    "groups_id": [
                        Command.link(
                            self.env.ref("disbursement.group_disbursement_user").id
                        )
                    ],
                }
            )
        )
        dr = self._request(900_000, [100_000])
        with self.assertRaises(AccessError):
            dr.with_user(user).write({"is_apportioned": False})
