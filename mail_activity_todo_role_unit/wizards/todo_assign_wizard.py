from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TodoAssignWizard(models.TransientModel):
    """มอบหมายให้… — pick a user (limited to the role ∩ OU cohort) to hand a
    group Todo off to. Reachable from two places:

    - The alert on the source record's form (``todo.assignable`` mixin);
      context carries ``active_model`` + ``active_id`` of the source record.
      All claimable Todos on that record are reassigned in bulk.
    - The Todo Inbox tree/form on ``mail.activity``; context carries
      ``active_model = 'mail.activity'`` + ``active_ids = [<activity>]``.
    """

    _name = "todo.assign.wizard"
    _description = "Delegate a group Todo (มอบหมายให้…)"

    activity_ids = fields.Many2many(
        "mail.activity",
        string="Todos",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="ผู้รับมอบหมาย",
        required=True,
        help="Limited to users who hold the Todo's Responsible Role in its "
        "Operating Unit (ADR-0002).",
    )
    candidate_user_ids = fields.Many2many(
        "res.users",
        "todo_assign_wizard_candidate_rel",
        "wizard_id",
        "user_id",
        string="Candidate users",
    )

    @api.model
    def _resolve_target_activities(self):
        """Resolve the target activities from context.

        Two entry points:
        - From ``mail.activity`` Inbox: ``active_ids`` are already activities.
        - From a source record (``todo.assignable`` mixin): resolve claimable
          activities on that record.
        """
        ctx = self.env.context
        model = ctx.get("active_model")
        if model == "mail.activity":
            ids = ctx.get("active_ids") or (
                [ctx["active_id"]] if ctx.get("active_id") else []
            )
            activities = self.env["mail.activity"].browse(ids)
        elif model and ctx.get("active_id"):
            record = self.env[model].browse(ctx["active_id"])
            activities = record._claimable_todo_activities()
        else:
            activities = self.env["mail.activity"]
        # Only group Todos are delegatable (ADR-0002).
        return activities.filtered("responsible_role_id")

    @api.model
    def _candidate_users(self, activities):
        """Union of role ∩ OU membership across all target activities."""
        candidates = self.env["res.users"]
        for act in activities:
            if not act.responsible_role_id or not act.operating_unit_id:
                continue
            candidates |= (
                act.responsible_role_id.sudo().user_ids
                & act.operating_unit_id.sudo().user_ids
            )
        return candidates

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        activities = self._resolve_target_activities()
        if not activities:
            raise UserError(_("ไม่มี Todo ที่มอบหมายได้บนรายการนี้"))
        vals["activity_ids"] = [(6, 0, activities.ids)]
        vals["candidate_user_ids"] = [(6, 0, self._candidate_users(activities).ids)]
        return vals

    def action_confirm(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("กรุณาเลือกผู้รับมอบหมาย"))
        if self.user_id not in self.candidate_user_ids:
            raise UserError(
                _("ผู้รับมอบหมายต้องอยู่ในกลุ่ม role ∩ operating unit ของ Todo")
            )
        self.activity_ids.action_reassign(self.user_id)
        return {"type": "ir.actions.act_window_close"}
