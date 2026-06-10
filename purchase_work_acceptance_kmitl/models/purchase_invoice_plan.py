# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseInvoicePlan(models.Model):
    _inherit = "purchase.invoice.plan"

    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="WA Reference",
        store=False,
        readonly=True,
        compute="_compute_wa_id",
    )
    wa_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("accept", "Accepted"),
            ("cancel", "Cancelled"),
        ],
        string="WA Status",
        store=False,
        readonly=True,
        compute="_compute_wa_id",
    )
    deliverables = fields.Text(
        string="Deliverables",
    )

    @api.depends(
        "purchase_id.wa_line_ids.wa_id.installment_id",
        "purchase_id.wa_line_ids.wa_id.state",
    )
    def _compute_wa_id(self):
        for rec in self:
            wa = self.env["work.acceptance"].search(
                [("installment_id", "=", rec.id), ("state", "!=", "cancel")],
                limit=1,
                order="id desc",
            )
            rec.wa_id = wa.id
            rec.wa_state = wa.state
