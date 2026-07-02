from lxml import etree

from odoo import api, fields, models
from odoo.tools.misc import frozendict


class TodoAssignable(models.AbstractModel):
    """Mixin that surfaces Claim/Delegate buttons for group Todos on the source
    record's form (ADR-0002 Claim ergonomics).

    Inheriting this mixin from a business model auto-injects an alert box with
    two buttons above the sheet — mirroring how ``base_tier_validation`` injects
    its label above the sheet via a ``get_view`` override. Consumers do not
    edit their own form XML.
    """

    _name = "todo.assignable"
    _description = "Todo Assignable (mixin)"
    _inherit = "mail.activity.mixin"

    has_claimable_todo = fields.Boolean(
        compute="_compute_has_claimable_todo",
        compute_sudo=True,
        help="Technical: whether the current user has a group Todo on this "
        "record they could Claim (role ∩ OU match, user_id empty).",
    )

    @api.depends(
        "activity_ids.user_id",
        "activity_ids.responsible_role_id",
        "activity_ids.operating_unit_id",
    )
    @api.depends_context("uid")
    def _compute_has_claimable_todo(self):
        user = self.env.user
        role_ids = set(user.todo_role_ids.ids)
        ou_ids = set(user.operating_unit_ids.ids)
        for record in self:
            record.has_claimable_todo = (
                bool(role_ids)
                and bool(ou_ids)
                and any(
                    not act.user_id
                    and act.responsible_role_id.id in role_ids
                    and act.operating_unit_id.id in ou_ids
                    for act in record.activity_ids
                )
            )

    def _claimable_todo_activities(self):
        """Return activities on this record the current user can Claim."""
        self.ensure_one()
        user = self.env.user
        role_ids = user.todo_role_ids.ids
        ou_ids = user.operating_unit_ids.ids
        if not role_ids or not ou_ids:
            return self.env["mail.activity"]
        return self.activity_ids.filtered(
            lambda a: not a.user_id
            and a.responsible_role_id.id in role_ids
            and a.operating_unit_id.id in ou_ids
        )

    def action_claim_todo_on_record(self):
        """มอบหมายให้ฉัน — bulk-claim every claimable group Todo on this record."""
        self.ensure_one()
        self._claimable_todo_activities().action_claim()
        return True

    def action_reassign_todo_on_record(self):
        """มอบหมายให้… — open the delegate wizard for this record."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "มอบหมายให้...",
            "res_model": "todo.assign.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": self._name,
                "active_id": self.id,
            },
        }

    # ------------------------------------------------------------------
    # Auto-inject the assignment alert above the sheet, following the
    # base_tier_validation label pattern (tier_validation.py:838-845).
    # ------------------------------------------------------------------
    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return res
        View = self.env["ir.ui.view"]
        doc = etree.XML(res["arch"])
        sheet_nodes = doc.xpath("/form/sheet")
        if not sheet_nodes:
            return res
        rendered = self.env["ir.qweb"]._render(
            "mail_activity_todo_role_unit.todo_assignment_alert"
        )
        template_node = etree.fromstring(rendered)
        new_arch, new_models = View.postprocess_and_fields(template_node, self._name)
        template_node = etree.fromstring(new_arch)
        for sheet in sheet_nodes:
            for child in template_node:
                sheet.addprevious(child)
        all_models = dict(res["models"])
        for model, view_fields in new_models.items():
            if model in all_models:
                all_models[model] = tuple(set(all_models[model]) | set(view_fields))
            else:
                all_models[model] = tuple(view_fields)
        res["arch"] = etree.tostring(doc)
        res["models"] = frozendict(all_models)
        return res
