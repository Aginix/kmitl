# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SelectWorkAcceptanceWizard(models.TransientModel):
    _inherit = 'work.accepted.date.wizard'

    document_ids = fields.One2many(
        'purchase.work.acceptance.attachment',
        'wizard_id',
        string='Attachments',
    )

    def button_accept(self):
        if not self.document_ids:
            raise ValidationError("You must upload at least one file before accepting.")

        work_acceptance = self.env['work.acceptance'].browse(self.env.context.get('active_id'))

        # Move attachments to work.acceptance
        self.document_ids.write({
            'wizard_id': False,
            'wa_id': work_acceptance.id,
        })

        return work_acceptance.with_context(manual_date_accept=False).button_accept(force=self.date_accept)