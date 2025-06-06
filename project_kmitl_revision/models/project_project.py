import logging

from odoo import fields, models

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
        vals.pop("active", None)
        return vals

    def _get_new_rev_data(self, new_rev_number):
        self.ensure_one()
        return {
            "revision_number": new_rev_number,
            "unrevisioned_name": self.unrevisioned_name,
            "name": self.unrevisioned_name,
            "old_revision_ids": [(4, self.id, False)],
        }

    def action_view_revisions(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "project.open_view_project_all"
        )
        result["domain"] = ["|", ("active", "=", False), ("active", "=", True)]
        result["context"] = {
            "active_test": 0,
            "search_default_current_revision_id": self.id,
            "default_current_revision_id": self.id,
            "create": False,
        }
        return result

    def action_approve(self):
        for record in self:
            record.state = "approve"
        old_revisions = self.env["project.project"].search(
            [("current_revision_id", "=", self.id)]
        )
        old_revisions.write({"state": "revised"})

    def open_project(self):
        self.ensure_one()
        target_id = self.current_revision_id.id if self.current_revision_id else self.id
        return {
            "name": "project",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "project.project",
            "target": "current",
            "res_id": target_id,
        }
