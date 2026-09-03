# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import WithholdingTaxRemittanceCommon


@tagged("post_install", "-at_install")
class TestWithholdingTaxRemittance(WithholdingTaxRemittanceCommon):
    def test_cert_starts_pending(self):
        cert = self._make_cert()
        self.assertEqual(cert.remit_state, "pending")
        self.assertEqual(cert.amount_total, 300.0)

    def test_create_remittance_from_certs(self):
        cert1 = self._make_cert(amount=300.0)
        cert2 = self._make_cert(amount=150.0)
        action = (cert1 | cert2).action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])

        self.assertEqual(remittance.state, "draft")
        self.assertEqual(remittance.income_tax_form, "pnd53")
        self.assertEqual(remittance.wht_account_id, self.wht_account_53)
        self.assertEqual(remittance.amount_total, 450.0)
        self.assertEqual(remittance.cert_ids, cert1 | cert2)
        self.assertEqual(remittance.period_month, "1")
        self.assertEqual(remittance.period_year, "2569")

    def test_create_remittance_mixed_form_raises(self):
        cert_53 = self._make_cert(income_tax_form="pnd53")
        cert_1 = self._make_cert(income_tax_form="pnd1", wht_tax=self.wht_tax_1)
        with self.assertRaises(UserError):
            (cert_53 | cert_1).action_create_remittance()

    def test_create_remittance_mixed_account_same_form_raises(self):
        other_account = self.env["account.account"].create(
            {
                "code": "212098",
                "name": "Another PND53 payable",
                "account_type": "liability_current",
                "wht_account": True,
                "company_id": self.company.id,
            }
        )
        other_wht_tax = self.env["account.withholding.tax"].create(
            {
                "name": "WHT 3% (53) alt",
                "account_id": other_account.id,
                "amount": 3.0,
                "income_tax_form": "pnd53",
                "company_id": self.company.id,
            }
        )
        cert1 = self._make_cert(income_tax_form="pnd53")
        cert2 = self._make_cert(income_tax_form="pnd53", wht_tax=other_wht_tax)
        with self.assertRaises(UserError):
            (cert1 | cert2).action_create_remittance()

    def test_create_remittance_not_done_raises(self):
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": self.vendor.id,
                "income_tax_form": "pnd53",
                "date": "2026-01-15",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            cert.action_create_remittance()

    def test_action_post_creates_balanced_move_and_marks_certs(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        action = (cert1 | cert2).action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
                "partner_id": self.rd_partner.id,
            }
        )

        remittance.action_post()

        self.assertEqual(remittance.state, "posted")
        self.assertNotEqual(remittance.name, "/")
        self.assertTrue(remittance.name.startswith("WHTR/"))
        self.assertEqual(remittance.move_id.state, "posted")

        move = remittance.move_id
        self.assertEqual(len(move.line_ids), 4)
        self.assertEqual(sum(move.line_ids.mapped("debit")), 450.0)
        self.assertEqual(sum(move.line_ids.mapped("credit")), 450.0)
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

        self.assertEqual(cert1.remit_state, "remitted")
        self.assertEqual(cert2.remit_state, "remitted")

    def test_action_post_requires_bank_account(self):
        cert = self._make_cert()
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        remittance.journal_id = self.journal_general
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_action_cancel_reverses_move_and_restores_certs(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance = self._make_remittance(cert)
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        remittance.action_post()
        posted_move = remittance.move_id

        remittance.action_cancel()

        self.assertEqual(remittance.state, "cancelled")
        self.assertFalse(remittance.move_id)
        # The plain JE is reversed, not cancelled: _reverse_moves(cancel=True)
        # only reconciles reconcilable/cash lines against the reversal, it
        # never flips the original move's state.
        self.assertEqual(posted_move.state, "posted")
        reversal_move = self.env["account.move"].search(
            [("reversed_entry_id", "=", posted_move.id)]
        )
        self.assertTrue(reversal_move)
        wht_lines = (posted_move.line_ids | reversal_move.line_ids).filtered(
            lambda l: l.account_id == self.wht_account_53
        )
        self.assertEqual(sum(wht_lines.mapped("balance")), 0.0)
        self.assertFalse(cert.remittance_id)
        self.assertEqual(cert.remit_state, "pending")

    def test_remit_state_persists_across_cert_reopen(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        remittance.action_post()
        self.assertEqual(cert.remit_state, "remitted")

        # Simulate the source document being reopened and redone: the
        # remittance link must not be an incidental side effect that a
        # base-module transition wipes out.
        cert.action_draft()
        cert.action_done()

        self.assertEqual(cert.remittance_id, remittance)
        self.assertEqual(cert.remit_state, "remitted")

    def test_action_load_pending_certs(self):
        cert1 = self._make_cert(amount=100.0)
        cert2 = self._make_cert(amount=200.0)
        remittance = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
            }
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert1 | cert2)
        self.assertEqual(remittance.amount_total, 300.0)

    def test_cancel_records_what_it_held(self):
        cert = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance = self._make_remittance(cert)
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        remittance.action_post()

        remittance.action_cancel()

        self.assertFalse(cert.remittance_id)
        self.assertFalse(remittance.cert_ids)
        last_message = remittance.message_ids.sorted(key=lambda m: m.id)[-1]
        self.assertIn(cert.name, last_message.body)

    def test_cert_on_another_draft_cannot_be_claimed(self):
        cert = self._make_cert(amount=300.0)
        action = cert.action_create_remittance()
        remittance1 = self.env["withholding.tax.remittance"].browse(action["res_id"])

        with self.assertRaises(UserError):
            cert.action_create_remittance()

        self.assertEqual(remittance1.cert_ids, cert)

    def test_copy_does_not_duplicate_certs(self):
        cert = self._make_cert(amount=300.0)
        remittance = self._make_remittance(cert)
        count_before = self.env["withholding.tax.cert"].search_count([])

        copy = remittance.copy(default={"period_month": "2"})

        self.assertEqual(
            self.env["withholding.tax.cert"].search_count([]), count_before
        )
        self.assertFalse(copy.cert_ids)

    def test_certs_without_income_tax_form_raise(self):
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": self.vendor.id,
                "date": "2026-01-15",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "wht_tax_id": self.wht_tax_53.id,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        cert.action_done()
        with self.assertRaises(UserError):
            cert.action_create_remittance()

    def test_move_has_one_line_pair_per_cert(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        remittance = self._make_remittance(cert1 | cert2)
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )

        remittance.action_post()

        move = remittance.move_id
        self.assertEqual(len(move.line_ids), 4)
        for cert in (cert1, cert2):
            cert_lines = move.line_ids.filtered(
                lambda l, cert=cert: cert.name in (l.name or "")
            )
            self.assertEqual(len(cert_lines), 2)
            debit_line = cert_lines.filtered("debit")
            credit_line = cert_lines.filtered("credit")
            self.assertEqual(debit_line.debit, cert.amount_total)
            self.assertEqual(credit_line.credit, cert.amount_total)
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_move_lines_carry_source_analytic(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        cert2 = self._make_cert(amount=150.0, analytic_distribution=self.distribution_b)
        remittance = self._make_remittance(cert1 | cert2)
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )

        remittance.action_post()

        move = remittance.move_id
        lines_a = move.line_ids.filtered(
            lambda l: l.analytic_distribution == self.distribution_a
        )
        lines_b = move.line_ids.filtered(
            lambda l: l.analytic_distribution == self.distribution_b
        )
        self.assertEqual(len(lines_a), 2)
        self.assertEqual(len(lines_b), 2)
        self.assertEqual(sum(lines_a.mapped("balance")), 0.0)
        self.assertEqual(sum(lines_b.mapped("balance")), 0.0)

    def test_post_raises_when_cert_has_no_analytic(self):
        cert = self._make_cert(amount=300.0)
        remittance = self._make_remittance(cert)
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_duplicate_form_and_period_raises(self):
        cert1 = self._make_cert(amount=300.0, analytic_distribution=self.distribution_a)
        remittance1 = self._make_remittance(cert1)

        with self.assertRaises(ValidationError):
            self.env["withholding.tax.remittance"].create(
                {
                    "income_tax_form": "pnd53",
                    "period_month": "1",
                    "period_year": "2569",
                }
            )

        remittance1.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        remittance1.action_post()
        remittance1.action_cancel()

        remittance2 = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
            }
        )
        self.assertEqual(remittance2.state, "draft")

    def test_cert_outside_period_raises_on_post(self):
        cert = self._make_cert(
            amount=300.0, date="2026-02-15", analytic_distribution=self.distribution_a
        )
        remittance = self._make_remittance(cert, month="1", year="2569")
        remittance.write(
            {
                "bank_account_id": self.bank_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        with self.assertRaises(UserError):
            remittance.action_post()

    def test_load_pending_certs_filters_by_period(self):
        cert_jan = self._make_cert(amount=100.0, date="2026-01-10")
        self._make_cert(amount=200.0, date="2026-02-10")
        remittance = self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": "pnd53",
                "period_month": "1",
                "period_year": "2569",
            }
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert_jan)
