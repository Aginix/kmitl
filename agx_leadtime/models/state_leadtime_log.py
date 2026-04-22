from odoo import models, fields, api


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

    def _log_transition(self, record, from_state, to_state, entry_date=None):
        now = fields.Datetime.now()
        duration_minutes = 0.0

        if entry_date:
            delta = now - entry_date
            duration_minutes = delta.total_seconds() / 60

        self.create({
            'res_model': record._name,
            'res_id': record.id,
            'from_state': from_state,
            'to_state': to_state,
            'duration_minutes': duration_minutes,
        })

    @api.model
    def get_stats(self, res_model, from_state, to_state):
        """
        ดึงสถิติ avg/min/max สำหรับ dashboard
        
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
        """
        ดึงสถิติทุก transition ของ model นั้น สำหรับ dashboard แบบ overview
        
        Usage:
            self.env['state.leadtime.log'].get_all_stats('purchase.order')
        """
        # หา unique transitions ทั้งหมดของ model นี้
        self.env.cr.execute("""
            SELECT DISTINCT from_state, to_state
            FROM state_leadtime_log
            WHERE res_model = %s
            ORDER BY from_state, to_state
        """, [res_model])

        transitions = self.env.cr.fetchall()

        return [
            self.get_stats(res_model, from_state, to_state)
            for from_state, to_state in transitions
        ]