# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestOperatingUnit(ReceiptKmitlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ou = cls.env["operating.unit"].create(
            {
                "name": "Test OU",
                "code": "TOU",
                "partner_id": cls.company.partner_id.id,
            }
        )

    def test_posted_receipt_stamps_ou_on_move_header_and_lines(self):
        receipt = self._make_receipt()
        receipt.operating_unit_id = self.ou
        receipt.action_confirm()
        receipt.action_post()
        self.assertEqual(receipt.move_id.operating_unit_id, self.ou)
        for line in receipt.move_id.line_ids:
            self.assertEqual(line.operating_unit_id, self.ou)
