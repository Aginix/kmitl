# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptLifecycle(ReceiptKmitlCommon):
    def test_create_mints_number_no_move(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.amount_total, 5000.0)
        self.assertFalse(receipt.move_id)
        fy_be = str(receipt._get_fy_be())
        self.assertTrue(receipt.name.startswith("RC/%s/" % fy_be))

    def test_rejected_create_does_not_burn_a_number(self):
        """A save rejected by a constraint must give the number back."""
        seq = self._make_receipt()._get_receipt_sequence()
        self.assertEqual(seq.implementation, "no_gap")
        number_next = seq.number_next_actual
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env["kmitl.receipt"].create(
                {
                    "department_analytic_id": self.dept_a.id,
                    "payment_method_id": self.pm_cash.id,
                    "partner_id": self.walkin.id,
                }
            )
        self.assertEqual(seq.number_next_actual, number_next)

    def test_post_creates_move(self):
        receipt = self._make_receipt(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        receipt._action_post()

        self.assertEqual(receipt.state, "done")
        self.assertTrue(receipt.move_id)
        self.assertEqual(receipt.move_id.state, "posted")

        cash_debit_lines = receipt.move_id.line_ids.filtered(
            lambda l: l.account_id == self.cash_account and l.debit
        )
        self.assertEqual(sum(cash_debit_lines.mapped("debit")), 5200.0)

        credit_lines = receipt.move_id.line_ids.filtered(
            lambda l: l.credit > 0 and l.account_id != self.cash_account
        )
        self.assertEqual(
            set(credit_lines.mapped("account_id")),
            {self.income_tuition, self.income_other},
        )
        self.assertEqual(sum(credit_lines.mapped("credit")), 5200.0)

        # Every debit is mirrored by a credit of the same total: N revenue
        # pairs plus the treasury-remittance pair.
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(sum(debit_lines.mapped("debit")), 5200.0 * 2)

    def test_post_uses_payment_method_account(self):
        receipt = self._make_receipt(method=self.pm_transfer)
        receipt._action_post()
        cash_debit_line = receipt.move_id.line_ids.filtered(
            lambda l: l.account_id == self.bank_account and l.debit
        )
        self.assertEqual(len(cash_debit_line), 1)
        self.assertEqual(cash_debit_line.debit, receipt.amount_total)
        self.assertEqual(receipt.move_id.journal_id, self.bank_journal)

    def test_post_matches_treasury_voucher_pattern(self):
        """Reproduces ledger voucher #3607097: Dr Cash Account paired 1:1
        with each revenue line, then a Dr Deposit Bank Account / Cr Cash
        Account pair remitting the full total to the treasury.
        """
        amounts = [4200.0, 1810.0, 20180.0, 4170.0]
        receipt = self._make_receipt(
            method=self.pm_transfer,
            lines=[(self.product_tuition, 1, amount) for amount in amounts],
        )
        receipt._action_post()
        lines = receipt.move_id.line_ids
        self.assertEqual(len(lines), 2 * len(receipt.line_ids) + 2)

        for line in receipt.line_ids:
            cash_debit = lines.filtered(
                lambda l: l.account_id == self.bank_account and l.debit == line.amount
            )
            revenue_credit = lines.filtered(
                lambda l: l.account_id == line.account_id and l.credit == line.amount
            )
            self.assertEqual(len(cash_debit), 1)
            self.assertEqual(len(revenue_credit), 1)
            self.assertEqual(
                cash_debit.analytic_distribution, line.analytic_distribution
            )
            self.assertEqual(
                revenue_credit.analytic_distribution, line.analytic_distribution
            )

        deposit_debit = lines.filtered(
            lambda l: l.account_id == self.deposit_account and l.debit
        )
        deposit_credit = lines.filtered(
            lambda l: l.account_id == self.bank_account and l.credit
        )
        self.assertEqual(len(deposit_debit), 1)
        self.assertEqual(len(deposit_credit), 1)
        self.assertEqual(deposit_debit.debit, receipt.amount_total)
        self.assertEqual(deposit_credit.credit, receipt.amount_total)
        self.assertEqual(
            deposit_debit.analytic_distribution, receipt.analytic_distribution
        )
        self.assertEqual(
            deposit_credit.analytic_distribution, receipt.analytic_distribution
        )

        self.assertEqual(sum(lines.mapped("debit")), sum(lines.mapped("credit")))
        for line in lines:
            self.assertTrue(line.analytic_distribution)

    def test_deposit_account_must_differ_from_cash_account(self):
        with self.assertRaises(ValidationError):
            self.env["kmitl.payment.method"].create(
                {
                    "name": "Bad Method",
                    "journal_id": self.cash_journal.id,
                    "account_id": self.cash_account.id,
                    "deposit_account_id": self.cash_account.id,
                }
            )

    def test_cancel_only_from_draft(self):
        receipt = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        remittance.action_submit()
        self.assertEqual(receipt.state, "submitted")
        with self.assertRaises(UserError):
            receipt.action_cancel()
        remittance.action_cancel()
        self.assertEqual(receipt.state, "draft")
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")

    def test_cannot_unlink_non_cancelled(self):
        receipt = self._make_receipt()
        with self.assertRaises(UserError):
            receipt.unlink()

    def test_header_analytic_syncs_to_lines(self):
        receipt = self._make_receipt()
        line = receipt.line_ids[0]
        self.assertTrue(line.analytic_distribution)
        self.assertIn(str(self.dept_a.id), line.analytic_distribution)

        receipt.write({"department_analytic_id": self.dept_b.id})
        self.assertIn(str(self.dept_b.id), line.analytic_distribution)
        self.assertNotIn(str(self.dept_a.id), line.analytic_distribution)

    def test_write_fund_analytic_syncs_json_and_lines(self):
        receipt = self._make_receipt()
        receipt.write({"fund_analytic_id": self.fund_a.id})
        self.assertIn(str(self.fund_a.id), receipt.analytic_distribution)
        self.assertIn(str(self.dept_a.id), receipt.analytic_distribution)
        line = receipt.line_ids[0]
        self.assertEqual(line.analytic_distribution, receipt.analytic_distribution)

    def test_write_analytic_distribution_directly_syncs_fields_and_lines(self):
        receipt = self._make_receipt()
        new_distribution = {
            str(self.dept_b.id): 100,
            str(self.source_a.id): 100,
            str(self.activity_a.id): 100,
        }
        receipt.write({"analytic_distribution": new_distribution})
        self.assertEqual(receipt.department_analytic_id, self.dept_b)
        self.assertEqual(receipt.source_analytic_id, self.source_a)
        self.assertEqual(receipt.activity_analytic_id, self.activity_a)
        line = receipt.line_ids[0]
        self.assertEqual(line.analytic_distribution, new_distribution)

    def test_removing_dimension_clears_stored_field(self):
        receipt = self._make_receipt(extra_vals={"source_analytic_id": self.source_a.id})
        self.assertEqual(receipt.source_analytic_id, self.source_a)
        distribution = dict(receipt.analytic_distribution)
        distribution.pop(str(self.source_a.id), None)
        receipt.write({"analytic_distribution": distribution})
        self.assertFalse(receipt.source_analytic_id)

    def test_onchange_all_dimensions_survive_together(self):
        """Regression: an earlier onchange design used one @api.onchange
        looping over all 6 codes. Each loop iteration reassigns
        analytic_distribution, and since every dimension field shares one
        reset-first compute, that wiped out the *other* fields' in-memory
        values before the loop read them — only the first code processed
        survived. Each dimension now has its own single-field onchange, so
        setting several pickers in the same form session must all land in
        the JSON together. write()/create() never exercised this: they go
        through the inverse directly, not onchange.
        """
        form = Form(self.env["kmitl.receipt"])
        form.department_analytic_id = self.dept_a
        form.fund_analytic_id = self.fund_a
        form.source_analytic_id = self.source_a
        form.activity_analytic_id = self.activity_a
        distribution = form.analytic_distribution
        self.assertIn(str(self.dept_a.id), distribution)
        self.assertIn(str(self.fund_a.id), distribution)
        self.assertIn(str(self.source_a.id), distribution)
        self.assertIn(str(self.activity_a.id), distribution)

    def test_new_line_on_saved_receipt_gets_analytic_distribution(self):
        receipt = self._make_receipt()
        receipt.write(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_card.id,
                            "name": self.product_card.name,
                            "account_id": self.income_other.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        },
                    )
                ]
            }
        )
        new_line = receipt.line_ids.filtered(
            lambda l: l.product_id == self.product_card
        )
        self.assertEqual(new_line.analytic_distribution, receipt.analytic_distribution)

    def test_reset_to_draft_from_cancelled(self):
        receipt = self._make_receipt()
        name = receipt.name
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        receipt.action_draft()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.name, name)

    def test_reset_to_draft_blocked_from_submitted(self):
        receipt = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        remittance.action_submit()
        with self.assertRaises(UserError):
            receipt.action_draft()

    def test_cancel_detaches_from_draft_remittance(self):
        receipt = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create({
            "department_analytic_id": self.dept_a.id,
            "receipt_ids": [(6, 0, [receipt.id])],
        })
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        self.assertFalse(receipt.remittance_id)
        self.assertNotIn(receipt.id, remittance.receipt_ids.ids)
        self.assertTrue(
            remittance.message_ids.filtered(lambda m: receipt.name in (m.body or ""))
        )
        # detached, so it can now be reset
        receipt.action_draft()
        self.assertEqual(receipt.state, "draft")

    def test_reset_blocked_while_remitted(self):
        receipt = self._make_receipt()
        receipt.action_cancel()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {"department_analytic_id": self.dept_a.id}
        )
        remittance.write({"receipt_ids": [(4, receipt.id)]})
        with self.assertRaises(UserError):
            receipt.action_draft()

    def test_constrains_requires_at_least_one_line(self):
        with self.assertRaises(ValidationError):
            self.env["kmitl.receipt"].create(
                {
                    "department_analytic_id": self.dept_a.id,
                    "payment_method_id": self.pm_cash.id,
                    "partner_id": self.walkin.id,
                }
            )

    def test_constrains_requires_positive_total(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(lines=[(self.product_tuition, 1, 0.0)])

    def test_payment_type_defaults_to_cash(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.payment_type, "cash")

    def test_payment_type_cheque_requires_number_and_date(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(
                method=self.pm_cheque,
                extra_vals={"cheque_number": False, "cheque_date": False},
            )

    def test_payment_type_cheque_with_fields_ok(self):
        receipt = self._make_receipt(method=self.pm_cheque)
        self.assertEqual(receipt.payment_type, "cheque")

    def test_payment_type_transfer_requires_date(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(
                method=self.pm_transfer, extra_vals={"transfer_date": False}
            )

    def test_payment_type_transfer_with_date_ok(self):
        receipt = self._make_receipt(method=self.pm_transfer)
        self.assertEqual(receipt.payment_type, "transfer")

    def test_payment_method_must_match_payment_type(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(
                method=self.pm_cash,
                extra_vals={
                    "payment_type": "transfer",
                    "transfer_date": fields.Date.context_today(self.env.user),
                },
            )

    def test_onchange_payment_type_clears_inactive_fields(self):
        receipt = self.env["kmitl.receipt"].new(
            {
                "department_analytic_id": self.dept_a.id,
                "payment_type": "cheque",
                "cheque_number": "123456",
                "cheque_date": fields.Date.context_today(self.env.user),
                "payment_method_id": self.pm_cash.id,
            }
        )
        receipt.payment_type = "cash"
        receipt._onchange_payment_type()
        self.assertFalse(receipt.cheque_number)
        self.assertFalse(receipt.cheque_date)
        self.assertFalse(receipt.payment_method_id)
