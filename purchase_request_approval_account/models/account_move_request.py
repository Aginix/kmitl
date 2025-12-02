# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequest(models.Model):
    _inherit = 'account.move.request'

    purchase_request_approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def action_view_purchase_approval(self):
        self.ensure_one()
        if not self.purchase_request_approval_id:
            raise UserError(_('No Purchase Request Approval linked to this request.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request Approval'),
            'res_model': 'purchase.request.approval',
            'res_id': self.purchase_request_approval_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _message_link_back_to_request(self):
        name = self.purchase_request_approval_id.name
        link = self.purchase_request_approval_id._get_record_url()

        return _(
            'This record has been created from: <a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )
