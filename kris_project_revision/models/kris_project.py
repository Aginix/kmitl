# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KrisProject(models.Model):
    _name = "kris.project"
    _inherit = ["kris.project", "base.revision"]

    # --- Revision (base.revision mixin) ---
    current_revision_id = fields.Many2one(
        comodel_name="kris.project",
        string="ฉบับแก้ไขล่าสุด",
        copy=False,
    )
    old_revision_ids = fields.One2many(
        comodel_name="kris.project",
        string="ฉบับแก้ไขก่อนหน้า",
    )
    revision_number = fields.Integer(string="ครั้งที่แก้ไข")
    revision_count = fields.Integer(string="จำนวนฉบับแก้ไข")

    _sql_constraints = [
        (
            "revision_unique",
            "unique(unrevisioned_name, revision_number, company_id)",
            "Project Number and revision must be unique per Company.",
        )
    ]

    # --- Revision (base.revision) ----------------------------------------

    def _get_new_rev_data(self, new_rev_number):
        # Carry the project name onto the new revision so copy() keeps it
        # verbatim instead of appending a "(copy)" suffix; only the Project
        # Number distinguishes revisions (KRIS0001 -> KRIS0001-01).
        vals = super()._get_new_rev_data(new_rev_number)
        vals["project_name"] = self.project_name
        return vals

    def create_revision(self):
        self.ensure_one()
        new = self.copy_revision_with_context()
        self.message_post(
            body=_("สร้างฉบับแก้ไขใหม่ %s — ฉบับนี้ถูกเก็บเป็นสำเนาเก่า")
            % new.name
        )
        new.message_post(
            body=_("สร้างจากฉบับเดิม %s (ฉบับแก้ไขครั้งที่ %s)")
            % (self.name, new.revision_number)
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": new.id,
            "target": "current",
        }

    def action_view_revisions(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "kris_project.action_kris_project"
        )
        action["domain"] = ["|", ("active", "=", False), ("active", "=", True)]
        action["context"] = {
            "active_test": 0,
            "search_default_current_revision_id": self.id,
            "default_current_revision_id": self.id,
        }
        return action
