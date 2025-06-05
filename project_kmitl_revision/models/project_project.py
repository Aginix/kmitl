# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="project.project",
    )
    old_revision_ids = fields.One2many(
        comodel_name="project.project",
    )

    def _prepare_revision_data(self, new_revision):
        vals = super()._prepare_revision_data(new_revision)
        vals.update({"state": "cancel"})
        return vals

    def action_view_revisions(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id("project.open_view_project_all")
        result["domain"] = ["|", ("active", "=", False), ("active", "=", True)]
        result["context"] = {
            "active_test": 0,
            "search_default_current_revision_id": self.id,
            "default_current_revision_id": self.id,
        }
        return result
