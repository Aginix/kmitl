from odoo import api, fields, models
from odoo.tools import is_html_empty


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    category_guideline = fields.Html(
        related="category_id.guideline_html",
        string="คำอธิบายแบบฟอร์ม",
        readonly=True,
    )
    show_category_guideline = fields.Boolean(
        compute="_compute_show_category_guideline",
    )

    @api.depends("category_guideline")
    def _compute_show_category_guideline(self):
        for rec in self:
            rec.show_category_guideline = not is_html_empty(rec.category_guideline)
