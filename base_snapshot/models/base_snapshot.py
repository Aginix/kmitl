# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BaseSnapshot(models.Model):
    _name = 'base.snapshot'
    _description = 'Base Snapshot'

    current_snapshot_id = fields.Many2one(
        comodel_name="base.snapshot",
        string="Current snapshot",
        readonly=True,
        copy=True,
    )
    old_snapshot_ids = fields.One2many(
        comodel_name="base.snapshot",
        inverse_name="current_snapshot_id",
        string="Old snapshots",
        readonly=True,
        domain=["|", ("active", "=", False), ("active", "=", True)],
        context={"active_test": False},
    )
    snapshot_number = fields.Integer(string="Snapshot", copy=False, default=0)
    unsnapshoted_name = fields.Char(
        string="Original Reference", copy=True, readonly=True
    )
    active = fields.Boolean(default=True)
    has_old_revisions = fields.Boolean(compute="_compute_has_old_snapshots")
    snapshot_count = fields.Integer(
        compute="_compute_snapshot_count", string="Previous snapshot count"
    )

    @api.depends("old_snapshot_ids")
    def _compute_snapshot_count(self):
        res = self.with_context(active_test=False).read_group(
            domain=[("current_snapshot_id", "in", self.ids)],
            fields=["current_snapshot_id"],
            groupby=["current_snapshot_id"],
        )
        snapshot_dict = {
            x["current_snapshot_id"][0]: x["current_snapshot_id_count"] for x in res
        }
        for rec in self:
            rec.snapshot_count = snapshot_dict.get(rec.id, 0)

    _sql_constraints = [
        (
            "snapshot_unique",
            "unique(unsnapshoted_name, snapshot_number)",
            "Reference and snapshot must be unique.",
        )
    ]

    def _get_snapshot_copy_fields(self):
        return {
            "unsnapshoted_name": self.unsnapshoted_name,
        }

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        default.update(self._get_snapshot_copy_fields())

        default["current_snapshot_id"] = False
        rec = super().copy(default)

        if not rec.unsnapshoted_name:
            name_field = self._context.get("snapshot_name_field", "name")
            rec.write({"unsnapshoted_name": rec[name_field]})

        return rec
