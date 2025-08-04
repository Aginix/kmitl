# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BaseSubstateType(models.Model):
    _inherit = "base.substate.type"

    model = fields.Selection(
        selection_add=[("purchase.request", "Purchase request")],
        ondelete={"purchase.request": "cascade"},
    )


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
            print("test ========>", rec.substate_id.name)
            if next_substate:
                rec.substate_id = next_substate.id
                rec.substate_updated = True

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
