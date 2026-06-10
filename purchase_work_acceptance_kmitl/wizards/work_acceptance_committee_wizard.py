# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptanceCommitteeWizard(models.TransientModel):
    _name = 'work.acceptance.committee.wizard'
    _description = _('WorkAcceptanceCommitteeWizard')

    wa_id = fields.Many2one(
        comodel_name='work.acceptance',
        string='Work Acceptance',
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name='work.acceptance.committee.wizard.line',
        inverse_name='wizard_id',
        string='Committee Results',
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        wa_id = self.env.context.get('default_wa_id')
        if wa_id:
            wa = self.env['work.acceptance'].browse(wa_id)
            lines = []
            for committee in wa.work_acceptance_committee_ids:
                lines.append((0, 0, {
                    'committee_id': committee.id,
                    'employee_name': committee.name,
                    'approve_role': committee.approve_role,
                    'status': committee.status,
                    'reason': committee.note,
                    'is_done': bool(committee.status),
                }))
            res['line_ids'] = lines
        return res

    def button_confirm(self):
        if any(not line.status for line in self.line_ids):
            raise UserError(_("Please fill in all the inspection results."))

        self.ensure_one()

        for line in self.line_ids:
            if line.is_done:
                continue
            line.committee_id.write({
                'status': line.status,
                'note': line.reason,
            })

        self.wa_id.with_context(
            skip_committee_wizard=True,
            manual_date_accept=False,
        ).button_accept(force=fields.Datetime.now())

        return {'type': 'ir.actions.act_window_close'}


class WorkAcceptanceCommitteeWizardLine(models.TransientModel):
    _name = 'work.acceptance.committee.wizard.line'
    _description = 'Work Acceptance Committee Result Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='work.acceptance.committee.wizard',
        ondelete='cascade',
    )
    committee_id = fields.Many2one(
        comodel_name='work.acceptance.committee',
        string='Committee Record',
        required=True,
    )
    employee_name = fields.Char(
        string='Committee Name',
        readonly=True,
    )
    approve_role = fields.Selection(
        selection=[
            ('chairman', 'Chairman'),
            ('committee', 'Committee'),
            ('secretary', 'Secretary'),
        ],
        string='Role',
        readonly=True,
    )
    status = fields.Selection(
        selection=[
            ('accept', 'Accept'),
            ('leave', 'Leave'),
            ('other', 'Other'),
        ],
        string='Status',
    )

    reason = fields.Text(string='Reason')

    is_done = fields.Boolean(
        string='Is Done',
        default=False,
    )
