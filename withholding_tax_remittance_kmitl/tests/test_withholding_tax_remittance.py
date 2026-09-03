# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
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
        cert1 = self._make_cert(amount=300.0)
        cert2 = self._make_cert(amount=150.0)
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
        self.assertEqual(len(move.line_ids), 2)
        debit_line = move.line_ids.filtered(lambda l: l.debit)
        credit_line = move.line_ids.filtered(lambda l: l.credit)
        self.assertEqual(debit_line.account_id, self.wht_account_53)
        self.assertEqual(debit_line.debit, 450.0)
        self.assertEqual(credit_line.account_id, self.bank_account)
        self.assertEqual(credit_line.credit, 450.0)
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
        cert = self._make_cert(amount=300.0)
        action = cert.action_create_remittance()
        remittance = self.env["withholding.tax.remittance"].browse(action["res_id"])
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
        self.assertEqual(posted_move.state, "cancel")
        self.assertFalse(cert.remittance_id)
        self.assertEqual(cert.remit_state, "pending")

    def test_remit_state_persists_across_cert_reopen(self):
        cert = self._make_cert(amount=300.0)
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
            {"income_tax_form": "pnd53"}
        )
        remittance.action_load_pending_certs()
        self.assertEqual(remittance.cert_ids, cert1 | cert2)
        self.assertEqual(remittance.amount_total, 300.0)
