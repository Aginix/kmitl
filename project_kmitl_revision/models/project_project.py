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
    revision_number = fields.Integer(string="Version", copy=False, default=0)

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

    def create_revision_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.revision.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_project_id": self.id,
            },
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

    def open_project(self):
        self.ensure_one()
        target_id = self.id
        if self.current_revision_id and self.current_revision_id.state == "approve":
            target_id = self.current_revision_id.id
        else:
            current_revision = self.env["project.project"].search(
                [("id", "=", self.current_revision_id.id)]
            )
            approved_revisions = current_revision.old_revision_ids.filtered(
                lambda r: r.state == "approve"
            )
            if approved_revisions:
                target_id = approved_revisions[0].id
        return {
            "name": "project",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "project.project",
            "target": "current",
            "res_id": target_id,
        }
