# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunPosition(models.Model):
    """ตำแหน่งบริหาร — administrative/authority position catalog (ADR-0003).

    The canonical routing target and the capacity a หนังสือ is signed in
    (คณบดี, ผอ.กอง, อธิการบดี). Purpose-built for e-Saraban — NOT ``hr.job``
    (employment position) and NOT academic rank (ศ./รศ., which is display-only
    and lives on ``hr.employee``).

    A Position resolves to its current ``holder_ids`` at the moment a routing
    step becomes *active*; the engine snapshots that person-set onto the step
    (P2) so later org changes never rewrite history.
    """

    _name = "sarabun.position"
    _description = "Sarabun Administrative Position"
    _order = "sequence, name"

    name = fields.Char(string="Position", required=True, translate=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        help="Optional scope — the unit this post belongs to.",
    )
    parent_id = fields.Many2one(
        comodel_name="sarabun.position",
        string="Reports To",
        help="Optional hierarchy (org display / future acting chains).",
    )
    holder_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="sarabun_position_holder_rel",
        column1="position_id",
        column2="employee_id",
        string="ผู้ดำรงตำแหน่ง (Current Holders)",
        help="Current holder(s) of this post (HR personnel). Multi-holder is "
        "resolved first-to-act. Interim รักษาการ/มอบอำนาจ: add the acting person "
        "here temporarily (the acting-assignment model is phase-2). Only personnel "
        "with a linked user account can actually act.",
    )
    holder_count = fields.Integer(
        string="ผู้ดำรงตำแหน่ง",
        compute="_compute_holder_count",
    )

    @api.depends("holder_ids")
    def _compute_holder_count(self):
        for record in self:
            record.holder_count = len(record.holder_ids)

    # === Phase-2 seam (designed, not built in v1) ===
    # acting_assignment_ids = fields.One2many("sarabun.position.acting", "position_id")
    #   delegate user + capacity + validity window, feeding holder resolution.

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Position code must be unique!"),
    ]

    def _current_holder_employees(self, at_datetime=None):
        """The hr.employee holders of this Position (for display/preview).

        v1 returns ``holder_ids`` directly. The ``at_datetime`` parameter is the
        phase-2 seam for time-bounded acting assignments (รักษาการ).
        """
        self.ensure_one()
        return self.holder_ids

    def _current_holder_users(self, at_datetime=None):
        """res.users of the current holders (employees → their linked user).
        The engine acts by logged-in user, so holders without a user cannot act."""
        self.ensure_one()
        return self._current_holder_employees(at_datetime).mapped("user_id")

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            result.append((record.id, name))
        return result
