# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    approval_id = fields.Many2one('purchase.request.approval', string='Purchase Request Approval', readonly=True)
    approval_count = fields.Integer(string='Approval Count', compute='_compute_approval_count')

    def _compute_approval_count(self):
        for wa in self:
            wa.approval_count = 1 if wa.approval_id else 0

    def action_view_approval(self):
        self.ensure_one()
        if not self.approval_id:
            raise UserError(_("No Purchase Request Approval linked to this Work Acceptance."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request Approval'),
            'res_model': 'purchase.request.approval',
            'view_mode': 'form',
            'res_id': self.approval_id.id,
            'target': 'current',
        }
