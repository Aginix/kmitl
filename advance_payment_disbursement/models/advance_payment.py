from odoo import api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    disbursement_request_ids = fields.Many2many(
        comodel_name="disbursement.request",
        string="ใบเบิก",
        compute="_compute_disbursement_request_ids",
    )

    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_ids",
    )

    @api.depends("reference")
    def _compute_disbursement_request_ids(self):
        for rec in self:
            requests = self.env["disbursement.request"]
            if rec.reference and rec.reference._name == "purchase.request":
                pr = rec.reference
                requests = pr.approval_ids.mapped("disbursement_request_ids")
            rec.disbursement_request_ids = requests
            rec.disbursement_request_count = len(requests)
