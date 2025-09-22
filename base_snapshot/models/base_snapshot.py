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
        inverse_name="current_revision_id",
        string="Old snapshots",
        readonly=True,
        domain=["|", ("active", "=", False), ("active", "=", True)],
        context={"active_test": False},
    )
    snapshot_number = fields.Integer(string="Snapshot", copy=False, default=0)
    unsnapshoted_name = fields.Char(
        string="Original Reference", copy=True, readonly=True
    )
