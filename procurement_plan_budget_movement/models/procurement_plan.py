from odoo import fields, models

MOVEMENT_GROUPS = (
    "procurement_plan.group_procurement_plan_user,budget.group_budget_viewer"
)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    # Same audience as the movement list, computed as the user (not sudo) so
    # the count honours its record rules and matches what the list shows.
    budget_movement_count = fields.Integer(
        string="การเคลื่อนไหวงบ",
        compute="_compute_budget_movement_count",
        groups=MOVEMENT_GROUPS,
    )

    def _compute_budget_movement_count(self):
        groups = self.env["procurement.plan.budget.move.line"].read_group(
            [("plan_id", "in", self._origin.ids)], ["plan_id"], ["plan_id"]
        )
        counts = {g["plan_id"][0]: g["plan_id_count"] for g in groups}
        for rec in self:
            rec.budget_movement_count = counts.get(rec._origin.id, 0)

    def action_open_budget_movements(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "procurement_plan_budget_movement.action_procurement_plan_budget_move_line"
        )
        action["domain"] = [("plan_id", "=", self.id)]
        return action
