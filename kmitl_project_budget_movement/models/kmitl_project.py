from odoo import fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    # Same audience as the movement list, computed as the user (not sudo) so
    # the count honours its record rules and matches what the list shows.
    budget_movement_count = fields.Integer(
        string="การเคลื่อนไหวงบ",
        compute="_compute_budget_movement_count",
        groups="kmitl_project.group_kmitl_project_user,budget.group_budget_viewer",
    )

    def _compute_budget_movement_count(self):
        groups = self.env["kmitl.project.budget.move.line"].read_group(
            [("project_id", "in", self._origin.ids)], ["project_id"], ["project_id"]
        )
        counts = {g["project_id"][0]: g["project_id_count"] for g in groups}
        for rec in self:
            rec.budget_movement_count = counts.get(rec._origin.id, 0)

    def action_open_budget_movements(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "kmitl_project_budget_movement.action_kmitl_project_budget_move_line"
        )
        action["domain"] = [("project_id", "=", self.id)]
        return action
