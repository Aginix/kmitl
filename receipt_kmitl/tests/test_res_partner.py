# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestResPartner(ReceiptKmitlCommon):
    def test_cannot_delete_walkin_partner(self):
        with self.assertRaises(UserError):
            self.walkin.unlink()

    def test_can_archive_walkin_partner(self):
        self.walkin.active = False
        self.assertFalse(self.walkin.active)

    def test_walkin_deletable_once_config_points_elsewhere(self):
        other = self.env["res.partner"].create({"name": "Other Walk-in"})
        self.env["ir.config_parameter"].sudo().set_param(
            "receipt_kmitl.walkin_partner_id", other.id
        )
        self.walkin.unlink()
