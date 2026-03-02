# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    is_external = fields.Boolean(
        string="Use External Inspection",
        default=False,
        copy=False,
    )

    has_attachment = fields.Boolean(
        string='Has Attachment',
        compute='_compute_has_attachment',
    )

    @api.depends('attachment_ids')
    def _compute_has_attachment(self):
        for rec in self:
            rec.has_attachment = bool(rec.attachment_ids)

    @api.depends('review_ids', 'is_external')
    def _compute_need_validation(self):
        for rec in self:
            if rec.is_external:
                rec.need_validation = False
            else:
                super(WorkAcceptance, rec)._compute_need_validation()
    
    def action_view_wa(self):
        res = super().action_view_wa()
        res['context']['default_is_external'] = self.is_external
        return res

    def button_accept(self, force=False):
        for rec in self:
            if rec.is_external and not rec.has_attachment:
                raise UserError(
                    _("Please attach at least one supporting document file before clicking accept.")
                )
        return super().button_accept(force=force)
