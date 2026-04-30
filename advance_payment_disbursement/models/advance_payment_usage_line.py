from odoo import api, fields, models


class AdvancePaymentUsageLine(models.Model):
    _inherit = "advance.payment.usage.line"

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        ondelete="cascade",
    )

    source_display = fields.Char(
        string="Source",
        compute="_compute_source_display",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        compute="_compute_partner_id",
        store=True,
    )

    disbursement_state = fields.Selection(
        related="disbursement_request_id.state",
        string="Disbursement State",
    )

    @api.depends("disbursement_request_id", "disbursement_request_id.name")
    def _compute_source_display(self):
        for line in self:
            if line.disbursement_request_id:
                line.source_display = line.disbursement_request_id.name
            else:
                line.source_display = "บันทึกการใช้เงิน"

    @api.depends("disbursement_request_id", "disbursement_request_id.partner_id")
    def _compute_partner_id(self):
        for line in self:
            if line.disbursement_request_id:
                line.partner_id = line.disbursement_request_id.partner_id
            else:
                line.partner_id = False
