# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BatchSubcomponentWizard(models.TransientModel):
    _name = 'batch.subcomponent.wizard'
    _description = _('BatchSubcomponentWizard')

    batch_line_id = fields.Many2one('account.asset.batch.line', required=True)
    line_ids = fields.One2many(
        'batch.subcomponent.wizard.line',
        'wizard_id',
        string="Subcomponents"
    )

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for index, line in enumerate(self.line_ids, start=1):
            line.sequence = index

    def confirm(self):
        for wizard in self:
            for index, line in enumerate(wizard.line_ids, start=1):
                self.env['account.asset.batch.subcomponent'].create({
                    'batch_line_id': wizard.batch_line_id.id,
                    'name': line.name,
                    'sequence': index,
                })


class BatchSubcomponentWizardLine(models.TransientModel):
    _name = 'batch.subcomponent.wizard.line'
    _description = 'Subcomponent Line (Wizard)'

    wizard_id = fields.Many2one('batch.subcomponent.wizard', required=True, ondelete="cascade")
    sequence = fields.Integer(default=1)
    name = fields.Char(required=True)

    number = fields.Char(
        compute="_compute_number",
        store=True
    )

    @api.depends("wizard_id.batch_line_id.name", "sequence")
    def _compute_number(self):
        for rec in self:
            name_part = rec.wizard_id.batch_line_id.name or ''
            if rec.sequence and rec.sequence > 0:
                rec.number = f"{name_part} ({rec.sequence})"
            else:
                rec.number = name_part or ''