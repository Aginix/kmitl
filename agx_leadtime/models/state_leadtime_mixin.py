# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, _, api

_logger = logging.getLogger(__name__)


class StateLeadtimeMixin(models.AbstractModel):
    _name = 'state.leadtime.mixin'
    _description = 'Mixin for tracking leadtime between state transitions'

    # Name of the field to track (default: 'state')
    _state_field = 'state'

    # Whitelist: list of (from_state, to_state) tuples to track; None = track all
    # Example: [('pending', 'approved'), ('approved', 'done')]
    _tracked_transitions = None

    # Blacklist: list of (from_state, to_state) tuples to exclude; None = no exclusions
    # Supports '*' wildcard to match any state
    # Example: [('*', 'rejected'), ('draft', '*')]
    _excluded_transitions = None

    state_leadtime_ids = fields.One2many(
        comodel_name='state.leadtime.log',
        inverse_name='res_id',
        domain=lambda self: [('res_model', '=', self._name)],
        string='State Leadtime Logs',
    )

    state_entry_date = fields.Datetime(
        string='State Entry Date',
        copy=False,
    )

    def _should_track_transition(self, from_state, to_state):
        """Check whether this state transition should be tracked.

        Override in subclasses for custom logic, or use _excluded_transitions
        and _tracked_transitions class attributes instead.
        """
        if self._excluded_transitions:
            for ex_from, ex_to in self._excluded_transitions:
                if ex_from in ('*', from_state) and ex_to in ('*', to_state):
                    return False
        if self._tracked_transitions is None:
            return True
        return (from_state, to_state) in self._tracked_transitions

    def _register_hook(self):
        result = super()._register_hook()
        if self._abstract:
            return result
        state_field = self._fields.get(self._state_field)
        if not state_field or state_field.type != 'selection':
            return result
        sel = state_field.selection
        if callable(sel):
            selection = state_field._description_selection(self.env)
        else:
            selection = sel
        valid_keys = {k for k, _ in selection} | {'*'}
        for attr in ('_tracked_transitions', '_excluded_transitions'):
            cfg = getattr(self, attr, None)
            if not cfg:
                continue
            for from_key, to_key in cfg:
                for key in (from_key, to_key):
                    if key not in valid_keys:
                        _logger.warning(
                            "%s.%s contains unknown state key '%s' for field '%s'",
                            self._name, attr, key, self._state_field,
                        )
        return result

    def write(self, vals):
        tracked_field = self._state_field
        transitions = []
        now = fields.Datetime.now()
        if tracked_field in vals:
            new_state = vals[tracked_field]
            for record in self:
                from_state = record[tracked_field]
                if from_state != new_state and record._should_track_transition(from_state, new_state):
                    transitions.append((record, from_state, new_state, record.state_entry_date))
            vals['state_entry_date'] = now
        result = super().write(vals)
        for record, from_state, to_state, entry_date in transitions:
            self.env['state.leadtime.log']._log_transition(
                record=record,
                from_state=from_state,
                to_state=to_state,
                entry_date=entry_date,
                transition_date=now,
            )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        now = fields.Datetime.now()
        for vals in vals_list:
            vals.setdefault('state_entry_date', now)

        return super().create(vals_list)
