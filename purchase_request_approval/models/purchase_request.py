from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_id = fields.Many2one(
        "purchase.request.approval",
        string="PR2",
        ondelete="cascade",
    )
    has_approval = fields.Boolean(
        compute="_compute_has_approval",
    )

    def _compute_has_approval(self):
        for rec in self:
            rec.has_approval = bool(
                self.env['purchase.request.approval'].search_count([('request_id', '=', rec.id)])
            )

    @api.constrains('approval_id')
    def _check_unique_approval(self):
        """Ensure one-to-one: An Approval can only be linked to one Purchase Request."""
        for rec in self:
            if rec.approval_id and self.search_count([('approval_id', '=', rec.approval_id.id)]) > 1:
                raise ValidationError(
                    _("Approval %s is already linked to another Purchase Request.") % rec.approval_id.display_name
                )

    def action_create_approval(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }
