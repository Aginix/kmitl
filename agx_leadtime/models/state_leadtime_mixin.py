from odoo import api, models, fields


class StateLeadtimeMixin(models.AbstractModel):
    _name = 'state.leadtime.mixin'
    _description = 'Mixin for tracking leadtime between state transitions'

    _state_field = 'state'

    # [('pending', 'approved'), ('approved', 'done')]
    _tracked_transitions = None

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
        """
        ตรวจสอบว่า transition นี้ควร track ไหม
        Override method นี้ใน subclass เพื่อ logic ที่ซับซ้อนกว่านี้ได้
        """
        if self._tracked_transitions is None:
            return True
        return (from_state, to_state) in self._tracked_transitions

    def write(self, vals):
        tracked_field = self._state_field
        transitions = []
        if tracked_field in vals:
            for record in self:
                from_state = getattr(record, tracked_field)
                to_state = vals[tracked_field]
                if from_state != to_state and record._should_track_transition(from_state, to_state):
                    transitions.append((record, from_state, to_state, record.state_entry_date))

            if transitions:
                vals['state_entry_date'] = fields.Datetime.now()

        result = super().write(vals)
        for record, from_state, to_state, entry_date in transitions:
            self.env['state.leadtime.log']._log_transition(
                record=record, from_state=from_state,
                to_state=to_state, entry_date=entry_date,
            )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            vals.setdefault('state_entry_date', now)
        return super().create(vals_list)
