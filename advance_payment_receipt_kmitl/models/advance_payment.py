from odoo import _, api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    receipt_ids = fields.Many2many(
        comodel_name="kmitl.receipt",
        string="Receipts",
        compute="_compute_receipts",
    )
    receipt_count = fields.Integer(compute="_compute_receipts")

    @api.depends("return_line_ids.receipt_id")
    def _compute_receipts(self):
        for rec in self:
            receipts = rec.return_line_ids.mapped("receipt_id")
            rec.receipt_ids = receipts
            rec.receipt_count = len(receipts)

    def action_view_receipts(self):
        self.ensure_one()
        receipts = self.return_line_ids.mapped("receipt_id")
        action = {
            "type": "ir.actions.act_window",
            "name": _("Receipts"),
            "res_model": "kmitl.receipt",
        }
        if len(receipts) == 1:
            action.update(res_id=receipts.id, view_mode="form")
        else:
            action.update(
                view_mode="tree,form", domain=[("id", "in", receipts.ids)]
            )
        return action
