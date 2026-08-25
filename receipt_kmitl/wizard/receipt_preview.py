# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class KmitlReceiptPreview(models.TransientModel):
    _name = "kmitl.receipt.preview"
    _description = "Receipt Preview"

    receipt_id = fields.Many2one("kmitl.receipt", required=True, readonly=True)
    preview_html = fields.Html(readonly=True, sanitize=False)
