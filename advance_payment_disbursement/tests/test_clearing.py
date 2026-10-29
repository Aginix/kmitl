from contextlib import contextmanager
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestClearing(TransactionCase):
    """A ใบเบิกชดใช้เงินยืม (advance request) clears its loan at ตัดงบ
    (advance_payment ADR-0032)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env["disbursement.request"]
        cls.ou = cls.env.ref("operating_unit.main_operating_unit")
        cls.ou_other = cls.env["operating.unit"].create(
            {
                "name": "Other OU",
                "code": "APD-OTHER",
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.borrower = Users.create(
            {"name": "Borrower", "login": "apd_borrower", "email": "b@apd.test"}
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Borrower", "user_id": cls.borrower.id}
        )
        cls.partner = cls.employee.work_contact_id
        # Holds no right on loans: everything about the loan is read as sudo.
        cls.dr_user = Users.create(
            {
                "name": "DR Maker",
                "login": "apd_dr_user",
                "email": "dr@apd.test",
                "groups_id": [
                    (6, 0, [cls.env.ref("disbursement.group_disbursement_user").id])
                ],
                "operating_unit_ids": [(6, 0, cls.ou.ids)],
                "default_operating_unit_id": cls.ou.id,
            }
        )
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "APD Loan Type"}
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )

    def _loan(self, amount=1000.0, ou=None):
        loan = self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_amount": amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test",
                "operating_unit_id": (ou or self.ou).id,
            }
        )
        loan.write({"state": "approved"})
        loan.action_start()
        return loan

    def _request(self, loan, amount):
        return self.DR.create(
            {
                "payment_type": "advance",
                "advance_payment_id": loan.id,
                "operating_unit_id": self.ou.id,
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account.id,
                            "name": "line",
                            "amount": amount,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )

    @contextmanager
    def _consumable(self):
        """Stand the act's station gate and the budget ledger aside: the
        consume act then only books ``budget_consumed_amount``."""
        DR = type(self.DR)

        def consume(rec):
            if not rec.budget_consumed_amount:
                rec.budget_consumed_amount = rec.amount_total

        with (
            patch.object(DR, "_disbursement_check_act"),
            patch.object(DR, "_disbursement_act_done"),
            patch.object(DR, "_action_approve_budget", consume),
        ):
            yield

    def test_picker_offers_outstanding_loans_of_the_ou_as_sudo(self):
        loan = self._loan()
        closed = self._loan()
        closed.write({"state": "done"})
        other_ou = self._loan(ou=self.ou_other)
        Loan = (
            self.env["advance.payment"]
            .with_user(self.dr_user)
            .with_context(advance_payment_picker=True)
        )
        domain = [("state", "=", "in_progress"), ("operating_unit_id", "=", self.ou.id)]
        result = dict(Loan.name_search("", domain))
        self.assertIn(loan.id, result)
        self.assertNotIn(closed.id, result)
        self.assertNotIn(other_ou.id, result)
        self.assertEqual(
            result[loan.id], "%s — %s" % (loan.contract_number, self.employee.name)
        )
        # Found by the borrower's name too.
        self.assertIn(loan.id, dict(Loan.name_search("Borrow", domain)))

    def test_requester_reads_the_loan_figures(self):
        loan = self._loan()
        request = self._request(loan, 100.0).with_user(self.dr_user)
        self.assertEqual(request.advance_payment_amount_remaining, 1000.0)
        self.assertEqual(request.advance_payment_employee_id, self.employee)

    def test_submit_requires_a_loan(self):
        request = self._request(self._loan(), 100.0)
        request.advance_payment_id = False
        with self.assertRaises(UserError):
            request.action_submit()

    def test_payee_must_be_the_borrower(self):
        request = self._request(self._loan(), 100.0)
        other = self.env["res.partner"].create({"name": "Someone Else"})
        with self.assertRaises(ValidationError):
            request.line_ids.partner_id = other

    def test_loan_only_on_an_advance_request(self):
        loan = self._loan()
        request = self._request(loan, 100.0)
        with self.assertRaises(ValidationError):
            request.payment_type = "direct"
        # On the form, switching away from advance drops the loan.
        draft = self.DR.new({"payment_type": "direct", "advance_payment_id": loan.id})
        draft._onchange_payment_type_advance_payment()
        self.assertFalse(draft.advance_payment_id)

    def test_pays_no_money_out(self):
        request = self._request(self._loan(), 100.0)
        self.partner.bank_ids = [(0, 0, {"acc_number": "APD-123"})]
        self.assertFalse(request.pays_out)
        self.assertFalse(request.line_ids.partner_bank_id)
        self.assertFalse(request.line_ids._requires_partner_bank())

    def test_consume_over_remaining_is_refused(self):
        request = self._request(self._loan(amount=100.0), 150.0)
        with self._consumable(), self.assertRaises(UserError):
            request.action_consume_budget()
        self.assertFalse(request.budget_consumed_amount)

    def test_consume_on_a_closed_loan_is_refused(self):
        loan = self._loan()
        request = self._request(loan, 100.0)
        loan.write({"state": "done"})
        with self._consumable(), self.assertRaises(UserError):
            request.action_consume_budget()

    def test_consume_clears_closes_and_cancel_reopens(self):
        loan = self._loan(amount=300.0)
        first = self._request(loan, 100.0)
        second = self._request(loan, 200.0)
        with self._consumable():
            first.with_user(self.dr_user).action_consume_budget()
            self.assertEqual(loan.actual_expense_amount, 100.0)
            self.assertEqual(loan.amount_remaining, 200.0)
            self.assertEqual(loan.state, "in_progress")
            second.action_consume_budget()
        self.assertEqual(loan.amount_remaining, 0.0)
        self.assertEqual(loan.state, "done")
        self.assertTrue(loan.date_closed)
        self.assertEqual(loan.disbursement_request_count, 2)
        self.assertTrue(loan.disbursement_request_html)

        second.action_cancel()
        self.assertEqual(loan.actual_expense_amount, 100.0)
        self.assertEqual(loan.amount_remaining, 200.0)
        self.assertEqual(loan.state, "in_progress")
        self.assertFalse(loan.date_closed)

    def test_cancel_clearing_nothing_keeps_a_closed_loan_closed(self):
        loan = self._loan(amount=300.0)
        request = self._request(loan, 100.0)
        loan.write({"state": "done"})
        request.action_cancel()
        self.assertEqual(loan.state, "done")
