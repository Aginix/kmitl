# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    is_printed = fields.Boolean(
        string="Printed",
        readonly=True,
        copy=False,
        help="The หนังสือ has been printed from the request's print button.",
    )

    def action_print_sarabun_document(self):
        """The 'Print Disbursement Request' button: the หนังสือ's official PDF,
        opened in a new tab, and the request flagged as printed."""
        self.ensure_one()
        document = self.active_sarabun_document_id
        # sudo: a system mark, set whatever the printer's write access.
        self.sudo().is_printed = True
        return {
            "type": "ir.actions.act_url",
            "url": f"/sarabun/document/{document.id}/pdf?inline=1",
            "target": "new",
        }
