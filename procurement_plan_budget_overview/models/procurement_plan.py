from odoo import fields, models
from odoo.tools import float_round

MOVEMENT_GROUPS = (
    "procurement_plan.group_procurement_plan_user,budget.group_budget_viewer"
)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    # Same audience as the Plan Budget Movements, read as the user so its
    # record rules apply.
    budget_movement_ids = fields.One2many(
        "procurement.plan.budget.move.line",
        "plan_id",
        string="การเคลื่อนไหวงบประมาณ",
        readonly=True,
        groups=MOVEMENT_GROUPS,
    )
    budget_pending_amount = fields.Float(
        string="รอโอน",
        digits="Product Price",
        compute="_compute_account_movement_summary",
        groups=MOVEMENT_GROUPS,
        help="ยอดสุทธิของใบโอนที่อยู่ระหว่างดำเนินการ (ยังไม่นับในยอดได้รับ)",
    )
    budget_off_target_count = fields.Integer(
        string="รายการพิกัดไม่ตรง",
        compute="_compute_account_movement_summary",
        groups=MOVEMENT_GROUPS,
    )
    # What the reservation still holds (``total_reserved``): closing returns
    # the leftover.
    budget_reserved_total = fields.Float(
        string="จองแล้ว",
        digits="Product Price",
        compute="_compute_budget_unreserved",
        compute_sudo=True,
    )
    budget_unreserved = fields.Float(
        string="ได้รับแต่ยังไม่ได้จอง",
        digits="Product Price",
        compute="_compute_budget_unreserved",
        compute_sudo=True,
        help="ยอดที่ได้รับจัดสรรเกินยอดจอง เช่น จัดสรรเพิ่มหลังเริ่มเบิกจ่าย",
    )

    def _compute_account_movement_summary(self):
        groups = self.env["procurement.plan.budget.move.line"].read_group(
            [
                ("plan_id", "in", self._origin.ids),
                ("status", "in", ("in_progress", "off_target")),
            ],
            ["amount"],
            ["plan_id", "status"],
            lazy=False,
        )
        summary = {(g["plan_id"][0], g["status"]): g for g in groups}
        for rec in self:
            pending = summary.get((rec._origin.id, "in_progress"), {})
            off_target = summary.get((rec._origin.id, "off_target"), {})
            rec.budget_pending_amount = pending.get("amount") or 0.0
            rec.budget_off_target_count = off_target.get("__count", 0)

    def _compute_budget_unreserved(self):
        for rec in self:
            reserved = sum(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state != "cancel"
                ).mapped("total_reserved")
            )
            rec.budget_reserved_total = reserved
            rec.budget_unreserved = max(
                float_round(rec.budget_amount - reserved, 2), 0.0
            )

    def action_open_budget_overview(self):
        """Open บัญชีแผน — this plan in its overview view, through a stored
        action so a page reload stays on it."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "procurement_plan_budget_overview.action_procurement_plan_budget_overview"
        )
        action["res_id"] = self.id
        return action

    def action_open_plan_form(self):
        """Back to the plan form from บัญชีแผน, also after a reload."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (self.env.ref("procurement_plan.view_procurement_plan_form").id, "form")
            ],
            "target": "main",
        }

    def action_open_off_target_movements(self):
        action = self.action_open_budget_movements()
        action["context"] = {"search_default_off_target": 1}
        return action
