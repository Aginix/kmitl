# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError


class StateLeadtimeLog(models.Model):
    _name = 'state.leadtime.log'
    _description = 'State Transition Leadtime Log'
    _order = 'transition_date desc'

    res_model = fields.Char(
        string='Model',
        required=True,
        index=True,
    )
    res_id = fields.Many2oneReference(
        string='Record ID',
        model_field='res_model',
        index=True,
    )
    from_state = fields.Char(string='From State', required=True)
    to_state = fields.Char(string='To State', required=True)
    transition_date = fields.Datetime(
        string='Transition Date',
        default=fields.Datetime.now,
        required=True,
    )
    duration_minutes = fields.Float(
        string='Duration (Minutes)',
        digits=(16, 2),
        default=0.0,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Triggered By',
        default=lambda self: self.env.user,
        ondelete='set null',
    )

    def init(self):
        tools.create_index(
            self._cr,
            'state_leadtime_log_report_idx',
            self._table,
            ['res_model', 'from_state', 'to_state'],
        )
        tools.create_index(
            self._cr,
            'state_leadtime_log_transition_date_idx',
            self._table,
            ['transition_date'],
        )

    def write(self, vals):
        raise UserError(_("State leadtime log entries are immutable and cannot be modified."))

    def unlink(self):
        raise UserError(_("State leadtime log entries cannot be deleted."))

    @api.model
    def _log_transition(self, record, from_state, to_state, entry_date=None, transition_date=None):
        now = transition_date or fields.Datetime.now()
        duration_minutes = 0.0

        if entry_date:
            delta = now - entry_date
            duration_minutes = delta.total_seconds() / 60

        self.sudo().create({
            'res_model': record._name,
            'res_id': record.id,
            'from_state': from_state,
            'to_state': to_state,
            'transition_date': now,
            'duration_minutes': duration_minutes,
        })

    @api.model
    def get_stats(self, res_model, from_state, to_state):
        """Return avg/min/max duration statistics for a specific transition.

        Usage:
            self.env['state.leadtime.log'].get_stats(
                res_model='purchase.order',
                from_state='draft',
                to_state='purchase',
            )
        """
        logs = self.search([
            ('res_model', '=', res_model),
            ('from_state', '=', from_state),
            ('to_state', '=', to_state),
            ('duration_minutes', '>', 0),
        ])

        if not logs:
            return {
                'res_model': res_model,
                'from_state': from_state,
                'to_state': to_state,
                'avg_minutes': 0.0,
                'min_minutes': 0.0,
                'max_minutes': 0.0,
                'count': 0,
            }

        durations = logs.mapped('duration_minutes')
        return {
            'res_model': res_model,
            'from_state': from_state,
            'to_state': to_state,
            'avg_minutes': sum(durations) / len(durations),
            'min_minutes': min(durations),
            'max_minutes': max(durations),
            'count': len(durations),
        }

    @api.model
    def get_all_stats(self, res_model):
        """Return statistics for all transitions of a model, suitable for dashboard overviews.

        Usage:
            self.env['state.leadtime.log'].get_all_stats('purchase.order')
        """
        groups = self.read_group(
            domain=[
                ('res_model', '=', res_model),
                ('duration_minutes', '>', 0),
            ],
            fields=['from_state', 'to_state', 'duration_minutes:avg', 'duration_minutes:min', 'duration_minutes:max'],
            groupby=['from_state', 'to_state'],
            lazy=False,
        )

        return [
            {
                'res_model': res_model,
                'from_state': g['from_state'],
                'to_state': g['to_state'],
                'avg_minutes': g['duration_minutes:avg'],
                'min_minutes': g['duration_minutes:min'],
                'max_minutes': g['duration_minutes:max'],
                'count': g['__count'],
            }
            for g in groups
        ]
