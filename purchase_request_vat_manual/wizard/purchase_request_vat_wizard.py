from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestVatWizard(models.TransientModel):
    _name = "purchase.request.vat.wizard"
    _description = "Edit Purchase Request VAT"

    request_id = fields.Many2one("purchase.request", required=True, readonly=True)
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount_tax_computed = fields.Monetary(
        string="Computed VAT",
        compute="_compute_amount_tax_computed",
    )
    amount_tax_new = fields.Monetary(
        string="New VAT",
        compute="_compute_amount_tax_new",
        store=True,
        readonly=False,
    )

    @api.depends("request_id")
    def _compute_amount_tax_computed(self):
        for wizard in self:
            wizard.amount_tax_computed = wizard.request_id._get_computed_amount_tax()

    @api.depends("request_id")
    def _compute_amount_tax_new(self):
        for wizard in self:
            wizard.amount_tax_new = wizard.request_id.amount_tax

    def action_confirm(self):
        self.ensure_one()
        if self.amount_tax_new <= 0:
            raise UserError(
                _(
                    "The VAT amount must be greater than zero. "
                    "To remove VAT, please set the request to VAT Exclusive instead."
                )
            )
        diff = self.amount_tax_new - self.amount_tax_computed
        self.request_id.amount_tax_manual = (
            0.0 if self.currency_id.is_zero(diff) else self.amount_tax_new
        )
        return {"type": "ir.actions.act_window_close"}

    def action_reset(self):
        self.ensure_one()
        self.request_id.amount_tax_manual = 0.0
        return {"type": "ir.actions.act_window_close"}
