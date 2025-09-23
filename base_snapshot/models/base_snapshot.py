# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BaseSnapshot(models.Model):
    _name = 'base.snapshot'
    _description = 'Base Snapshot'

    current_snapshot_id = fields.Many2one(
        comodel_name="base.snapshot",
        string="Current snapshot",
        readonly=True,
        copy=True,
    )
    snapshot_ids = fields.One2many(
        comodel_name="base.snapshot",
        inverse_name="current_snapshot_id",
        string="Old snapshots",
        readonly=True,
        domain=["|", ("active", "=", False), ("active", "=", True)],
    )
    snapshot_number = fields.Integer(string="Snapshot", copy=False, default=0)
    active = fields.Boolean(default=True)
    snapshot_count = fields.Integer(
        compute="_compute_snapshot_count", string="Previous snapshot count"
    )

    @api.depends("snapshot_ids")
    def _compute_snapshot_count(self):
        for rec in self:
            count = self.search_count([
                ("current_snapshot_id", "=", rec.id),
                ("active", "=", False),
            ])
            rec.snapshot_count = count

    def _get_snapshot_name(self, new_number):
        return "%s-copy-%02d" % (self.name, new_number)

    def _get_snapshot_copy_fields(self):
        return {}

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update(self._get_snapshot_copy_fields())

        new_number = self.snapshot_number + 1
        default["name"] = self._get_snapshot_name(new_number)

        return super().copy(default)

    def create_snapshot(self):
        snapshot_ids = []
        for rec in self:
            new_number = rec.snapshot_number + 1
            default_data = {
                "snapshot_number": new_number,
                "current_snapshot_id": rec.id,
                "active": False,
            }
            default_data.update(rec._get_snapshot_copy_fields())
            new_snapshot = rec.copy(default_data)

            if hasattr(rec, "message_post"):
                msg = _("New snapshot created: %s") % new_snapshot.display_name
                rec.message_post(body=msg)

            snapshot_ids.append(new_snapshot.id)
            self.snapshot_number = new_number

        return {
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "name": _("Snapshots"),
            "res_model": self._name,
            "domain": [("id", "in", snapshot_ids), ("active", "=", False)],
            "target": "current",
        }
