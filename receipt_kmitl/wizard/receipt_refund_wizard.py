# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ReceiptRefundWizard(models.TransientModel):
    _name = "receipt.kmitl.refund.wizard"
    _description = "Receipt Refund Wizard"

    receipt_id = fields.Many2one(
        "receipt.kmitl",
        required=True,
        readonly=True,
    )
    refund_method = fields.Selection(
        [("cash", "Cash"), ("transfer", "Bank Transfer")],
        required=True,
        default="cash",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Refund Journal",
        required=True,
        domain="[('type', 'in', ['cash', 'bank'])]",
    )
    reason = fields.Text(required=True)
    line_ids = fields.One2many(
        "receipt.kmitl.refund.wizard.line",
        "wizard_id",
        string="Lines",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        receipt_id = self.env.context.get("default_receipt_id")
        if receipt_id:
            receipt = self.env["receipt.kmitl"].browse(receipt_id)
            res["line_ids"] = [
                (
                    0,
                    0,
                    {
                        "receipt_line_id": rl.id,
                        "amount": rl.amount,
                        "refund": False,
                    },
                )
                for rl in receipt.line_ids
            ]
        return res

    def action_create_refund(self):
        self.ensure_one()
        selected = self.line_ids.filtered(lambda wl: wl.refund)
        if not selected:
            raise ValidationError(_("Select at least one line to refund."))
        for wl in selected:
            if wl.amount <= 0:
                raise ValidationError(_("Refund amount must be positive."))
            if wl.amount > wl.receipt_line_id.amount:
                raise ValidationError(
                    _("Refund amount cannot exceed original line amount.")
                )
        refund = self.env["receipt.kmitl.refund"].create(
            {
                "receipt_id": self.receipt_id.id,
                "refund_method": self.refund_method,
                "journal_id": self.journal_id.id,
                "reason": self.reason,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_line_id": wl.receipt_line_id.id,
                            "amount": wl.amount,
                        },
                    )
                    for wl in selected
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Receipt Refund"),
            "res_model": "receipt.kmitl.refund",
            "view_mode": "form",
            "res_id": refund.id,
        }


class ReceiptRefundWizardLine(models.TransientModel):
    _name = "receipt.kmitl.refund.wizard.line"
    _description = "Receipt Refund Wizard Line"

    wizard_id = fields.Many2one(
        "receipt.kmitl.refund.wizard",
        required=True,
        ondelete="cascade",
    )
    receipt_line_id = fields.Many2one(
        "receipt.kmitl.line",
        required=True,
        readonly=True,
    )
    name = fields.Char(
        related="receipt_line_id.name",
        readonly=True,
    )
    original_amount = fields.Monetary(
        related="receipt_line_id.amount",
        readonly=True,
        currency_field="currency_id",
    )
    refund = fields.Boolean(string="Refund?", default=False)
    amount = fields.Monetary(
        string="Refund Amount",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="receipt_line_id.currency_id",
        readonly=True,
    )
