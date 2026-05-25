from odoo import fields, models


class UpdateActualAmountWizard(models.TransientModel):
    _name = "approval.update.actual.amount.wizard"
    _description = "Update Actual Amount Wizard"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        required=True,
    )

    line_ids = fields.One2many(
        comodel_name="approval.update.actual.amount.wizard.line",
        inverse_name="wizard_id",
        string="Lines",
    )

    def action_save(self):
        for line in self.line_ids:
            line.approval_line_id.actual_amount = line.actual_amount
        return {"type": "ir.actions.act_window_close"}


class UpdateActualAmountWizardLine(models.TransientModel):
    _name = "approval.update.actual.amount.wizard.line"
    _description = "Update Actual Amount Wizard Line"

    wizard_id = fields.Many2one(
        comodel_name="approval.update.actual.amount.wizard",
        required=True,
        ondelete="cascade",
    )

    approval_line_id = fields.Many2one(
        comodel_name="approval.request.line",
        string="Approval Line",
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="approval_line_id.currency_id",
        readonly=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="approval_line_id.partner_id",
        string="Payee",
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        related="approval_line_id.product_id",
        string="Expense",
        readonly=True,
    )

    total_amount = fields.Monetary(
        related="approval_line_id.total_amount",
        string="Total",
        currency_field="currency_id",
        readonly=True,
    )

    actual_amount = fields.Monetary(
        string="Actual Amount",
        currency_field="currency_id",
    )
