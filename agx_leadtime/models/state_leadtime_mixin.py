from odoo import models, fields


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
        auto_join=True,
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

        if tracked_field in vals:
            for record in self:
                from_state = getattr(record, tracked_field)
                to_state = vals[tracked_field]

                if from_state == to_state:
                    continue

                if record._should_track_transition(from_state, to_state):
                    self.env['state.leadtime.log']._log_transition(
                        record=record,
                        from_state=from_state,
                        to_state=to_state,
                    )

        return super().write(vals)