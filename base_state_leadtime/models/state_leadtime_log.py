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
        if self.env.context.get('_force_unlink_leadtime_logs'):
            return super().unlink()
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
    def get_stats(self, res_model, from_state, to_state, date_from=None, date_to=None,
                  res_ids=None, latest_only=False):
        """Return avg/min/max/total duration statistics for a specific transition.

        Args:
            date_from:   optional datetime — filter logs with transition_date >= date_from
            date_to:     optional datetime — filter logs with transition_date <= date_to
            res_ids:     optional list of ints — filter logs by res_id; mutually exclusive
                         with date_from/date_to (res_ids takes precedence when provided)
            latest_only: when True, keep only the most-recent log per res_id so that
                         records that went through multiple cycles don't skew averages
        """
        domain = [
            ('res_model', '=', res_model),
            ('from_state', '=', from_state),
            ('to_state', '=', to_state),
            ('duration_minutes', '>', 0),
        ]
        if res_ids is not None:
            domain.append(('res_id', 'in', res_ids))
        else:
            if date_from:
                domain.append(('transition_date', '>=', date_from))
            if date_to:
                domain.append(('transition_date', '<=', date_to))

        logs = self.search(domain)  # ordered transition_date desc by _order

        if latest_only:
            seen = set()
            unique_ids = []
            for log in logs:        # newest-first because of _order
                if log.res_id not in seen:
                    seen.add(log.res_id)
                    unique_ids.append(log.id)
            logs = self.browse(unique_ids)

        if not logs:
            return {
                'res_model': res_model,
                'from_state': from_state,
                'to_state': to_state,
                'avg_minutes': 0.0,
                'min_minutes': 0.0,
                'max_minutes': 0.0,
                'total_minutes': 0.0,
                'count': 0,
            }

        durations = logs.mapped('duration_minutes')
        total = sum(durations)
        return {
            'res_model': res_model,
            'from_state': from_state,
            'to_state': to_state,
            'avg_minutes': total / len(durations),
            'min_minutes': min(durations),
            'max_minutes': max(durations),
            'total_minutes': total,
            'count': len(durations),
        }

    @api.model
    def get_all_stats(self, res_model):
        """Return statistics for all transitions of a model, suitable for dashboard overviews.

        Usage:
            self.env['state.leadtime.log'].get_all_stats('purchase.order')
        """
        logs = self.search([
            ('res_model', '=', res_model),
            ('duration_minutes', '>', 0),
        ])

        buckets = {}
        for log in logs:
            key = (log.from_state, log.to_state)
            buckets.setdefault(key, []).append(log.duration_minutes)

        result = []
        for (from_state, to_state), durations in buckets.items():
            total = sum(durations)
            result.append({
                'res_model': res_model,
                'from_state': from_state,
                'to_state': to_state,
                'avg_minutes': total / len(durations),
                'min_minutes': min(durations),
                'max_minutes': max(durations),
                'count': len(durations),
            })
        return result
