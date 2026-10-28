# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    can_print_sarabun_document = fields.Boolean(
        compute="_compute_can_print_sarabun_document",
        help="The request has a live หนังสือ the Disbursement Printer can print.",
    )

    def _compute_can_print_sarabun_document(self):
        for record in self:
            record.can_print_sarabun_document = bool(
                record._get_printer_sarabun_document()
            )

    def _get_printer_sarabun_document(self):
        """The live หนังสือ (sudo), whether or not the user is on its route: the
        Disbursement Printer group prints it on the request's read access."""
        self.ensure_one()
        return (
            self.env["sarabun.document"]
            .sudo()
            .search(
                [
                    ("origin_model", "=", self._name),
                    ("origin_res_id", "=", self.id),
                    ("state", "not in", ("rejected", "cancelled")),
                ],
                order="id desc",
                limit=1,
            )
        )

    def action_print_sarabun_document(self):
        """The 'Print Disbursement Request' button: the หนังสือ's official PDF."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/disbursement/request/{self.id}/sarabun_pdf",
            "target": "new",
        }
