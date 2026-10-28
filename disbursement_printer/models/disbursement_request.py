# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def action_print_sarabun_document(self):
        """The 'Print Disbursement Request' button: the หนังสือ's official PDF."""
        self.ensure_one()
        return self.active_sarabun_document_id.action_print_report()
