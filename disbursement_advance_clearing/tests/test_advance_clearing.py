# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvanceClearing(TransactionCase):
    """A request that pays no money out is booked by a clearing entry
    (Dr expense / Cr advance receivable), not a bill (ADR 0009)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]
        cls.distribution = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": code.title(), "code": code}
            )
            account = Account.create({"name": "%s test" % code, "plan_id": plan.id})
            cls.distribution[str(account.id)] = 100
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.receivable = cls.env["account.account"].create(
            {
                "code": "1122999999",
                "name": "Test Advance Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test Clearing", "code": "TCAR", "type": "general"}
        )
        cls.company.write(
            {
                "advance_clearing_journal_id": cls.journal.id,
                "advance_clearing_account_id": cls.receivable.id,
            }
        )
        cls.borrower = cls.env["res.partner"].create({"name": "Borrower"})

    def _request(self, payment_type="advance"):
        request = self.env["disbursement.request"].create(
            {
                "payment_type": payment_type,
                "has_tax": False,
                "partner_type_id": self.borrower.partner_type_id.id,
                "analytic_distribution": self.distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.borrower.id,
                            "name": "Spent",
                            "amount": 700.0,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                ],
            }
        )
        request.state = "signed"
        return request

    def test_clearing_entry_books_expense_against_receivable(self):
        request = self._request()
        self.assertTrue(request.can_create_advance_clearing)
        self.assertFalse(request.can_create_bill)
        request.action_create_advance_clearing()
        move = request.advance_clearing_move_ids
        self.assertEqual(move.journal_id, self.journal)
        self.assertEqual(move.analytic_distribution, self.distribution)
        self.assertFalse(request.bill_ids, "a clearing entry is not a bill")
        debit = move.line_ids.filtered("debit")
        credit = move.line_ids.filtered("credit")
        self.assertEqual(debit.account_id, self.expense_account)
        self.assertEqual(debit.debit, 700.0)
        self.assertEqual(credit.account_id, self.receivable)
        self.assertEqual(credit.partner_id, self.borrower)
        self.assertEqual(credit.credit, 700.0)
        self.assertEqual(request.settlement_stage, "none")

    def test_posted_then_confirmed_walks_to_booked_and_back(self):
        request = self._request()
        request.action_create_advance_clearing()
        move = request.advance_clearing_move_ids
        with self.assertRaises(UserError):
            request.action_confirm_advance_clearing()
        move.action_post()
        self.assertEqual(request.settlement_stage, "billed")
        request.action_confirm_advance_clearing()
        self.assertEqual(request.settlement_stage, "booked")
        move.button_draft()
        self.assertEqual(request.settlement_stage, "none")
        self.assertFalse(request.advance_clearing_confirmer_id)

    def test_paying_acts_do_not_apply(self):
        request = self._request()
        with self.assertRaises(UserError):
            request.action_create_bill()
        self.assertFalse(
            request._disbursement_act_applicable("disbursement.audit_payment")
        )

    def test_paying_request_has_no_clearing(self):
        request = self._request(payment_type="direct")
        self.assertFalse(request.can_create_advance_clearing)
        with self.assertRaises(UserError):
            request.action_create_advance_clearing()

    def test_settings_required(self):
        self.company.advance_clearing_account_id = False
        with self.assertRaises(UserError):
            self._request().action_create_advance_clearing()
