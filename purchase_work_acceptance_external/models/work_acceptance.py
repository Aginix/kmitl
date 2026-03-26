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
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    has_attachment = fields.Boolean(
        string='Has Attachment',
        compute='_compute_has_attachment',
    )

    @api.depends('attachment_ids')
    def _compute_has_attachment(self):
        for rec in self:
            rec.has_attachment = bool(rec.attachment_ids)

    def _can_auto_accept(self):
        return not self.is_external or self.has_attachment

    def button_review(self):
        for rec in self:
            if rec.is_external and not rec.has_attachment:
                raise UserError(
                    _("Please attach at least one supporting document file before clicking accept.")
                )
        return super().button_review()

    def button_accept(self, force=False):
        if self.env.context.get('skip_committee_wizard'):
            if self.is_external and not self.has_attachment:
                raise UserError(
                    _("Please attach at least one supporting document file before clicking accept.")
                )
        return super().button_accept(force=force)
