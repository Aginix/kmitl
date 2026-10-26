from odoo import fields, models
from odoo.tools import float_round

MOVEMENT_GROUPS = "kmitl_project.group_kmitl_project_user,budget.group_budget_viewer"


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    # Same audience as the Project Budget Movements, read as the user so its
    # record rules apply (ADR-0007).
    budget_movement_ids = fields.One2many(
        "kmitl.project.budget.move.line",
        "project_id",
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
    # What the reservation still holds (budget's จองเงิน, ``total_reserved``),
    # not its approved cap ``budget_reserved``: closing returns the leftover.
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
        groups = self.env["kmitl.project.budget.move.line"].read_group(
            [
                ("project_id", "in", self._origin.ids),
                ("status", "in", ("in_progress", "off_target")),
            ],
            ["amount"],
            ["project_id", "status"],
            lazy=False,
        )
        summary = {(g["project_id"][0], g["status"]): g for g in groups}
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
        """Open บัญชีโครงการ (ADR-0012) — this project in its overview view,
        through a stored action so a page reload stays on it."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "kmitl_project_budget_overview.action_kmitl_project_budget_overview"
        )
        action["res_id"] = self.id
        return action

    def action_open_project_form(self):
        """Back to the project form from บัญชีโครงการ — also after a reload,
        which leaves no breadcrumb. ``main`` resets the breadcrumbs so going
        back and forth never stacks them."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (self.env.ref("kmitl_project.view_kmitl_project_form").id, "form")
            ],
            "target": "main",
        }

    def action_open_off_target_movements(self):
        action = self.action_open_budget_movements()
        action["context"] = {"search_default_off_target": 1}
        return action
