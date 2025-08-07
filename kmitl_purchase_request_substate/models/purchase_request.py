from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = ["purchase.request", "base.substate.mixin"]
    _name = "purchase.request"
    _state_field = "state"

    substate_updated = fields.Boolean(string="Substate Updated", default=False)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'draft':
            vals['substate_updated'] = False
        return super().write(vals)

    def action_set_substate(self):
        for rec in self:
            substate_model = self.env['base.substate']
            current = rec.substate_id

            next_substate = substate_model.search([
                ('model', '=', self._name),
                ('sequence', '>', current.sequence)
            ], order='sequence ASC', limit=1)
            if next_substate:
                rec.substate_id = next_substate.id
                rec.substate_updated = True
                rec.verified_by = self.env.user.id
                rec.date_verified = fields.Date.context_today(self)

    def action_reset_substate(self):
        for rec in self:
            substate_model = self.env['base.substate']
            current = rec.substate_id

            next_substate = substate_model.search([
                ('model', '=', self._name),
                ('sequence', '<', current.sequence)
            ], order='sequence DESC', limit=1)
            if next_substate:
                rec.substate_id = next_substate.id
                rec.substate_updated = False
                rec.verified_by = ''
                rec.date_verified = ''

