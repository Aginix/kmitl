# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.invoice_kmitl.tests.common import InvoiceKmitlCommon


@tagged("post_install", "-at_install")
class TestOperatingUnit(InvoiceKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ou_b = cls.env["operating.unit"].create(
            {
                "name": "Invoice Test OU B",
                "code": "ITOUB",
                "partner_id": cls.company.partner_id.id,
            }
        )

    def _make_submission(self, **extra):
        vals = {
            "department_analytic_id": self.dept_a.id,
            "operating_unit_id": self.ou.id,
            "approver_id": self.treasury.id,
        }
        vals.update(extra)
        return self.env["kmitl.invoice.submission"].create(vals)

    def test_entries_carry_the_operating_unit_of_the_invoice(self):
        # Not the acting user's default unit: the invoice's own.
        invoice = self._make_invoice(operating_unit_id=self.ou_b.id)
        self._issue(invoice, operating_unit_id=self.ou_b.id)
        self.assertEqual(invoice.move_id.operating_unit_id, self.ou_b)
        for line in invoice.move_id.line_ids:
            self.assertEqual(line.operating_unit_id, self.ou_b)

        invoice.action_receive_payment()
        self.assertEqual(invoice.receipt_id.operating_unit_id, self.ou_b)

    def test_pull_pending_invoices_excludes_other_operating_unit(self):
        mine = self._make_invoice()
        self._make_invoice(operating_unit_id=self.ou_b.id)
        submission = self._make_submission()
        submission.action_pull_pending_invoices()
        self.assertEqual(submission.invoice_ids, mine)

    def test_submit_raises_on_operating_unit_mismatch(self):
        other = self._make_invoice(operating_unit_id=self.ou_b.id)
        submission = self._make_submission(invoice_ids=[Command.set(other.ids)])
        with self.assertRaises(ValidationError):
            submission.action_submit()
