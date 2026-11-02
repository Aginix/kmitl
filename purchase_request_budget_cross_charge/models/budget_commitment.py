from odoo import _, api, models
from odoo.exceptions import UserError

_REQUEST_GROUP = "purchase_request_budget.group_purchase_request_budget_commit"


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    # --- ถัวจ่าย on a พ.1's slip (ADR-0020) ---

    @api.depends("purchase_request_ids.state")
    def _compute_split_editable(self):
        """A พ.1's slip has two windows: draft while the พ.1 waits for its
        reservation, and reserved-but-unused while it waits to be sent to
        e-Saraban (the letter renders the split live from then on)."""
        super()._compute_split_editable()
        for record in self:
            requests = record.sudo().purchase_request_ids
            if requests and record._is_split_capable():
                record.split_editable = len(
                    requests
                ) == 1 and record._is_request_split_window(requests)

    def _is_request_split_window(self, request):
        self.ensure_one()
        if self.state == "draft":
            # to_approve: re-reserving after the slip was cancelled (ADR-0010).
            return request.state in ("to_verify_budget", "to_approve")
        return (
            self.state == "reserved"
            and request.state == "to_approve"
            and not self.line_ids.filtered(
                lambda line: (
                    line.state == "posted"
                    and (line.move_type != "reserve" or line.is_return)
                )
            )
        )

    def _get_split_owner(self):
        return self.sudo().purchase_request_ids[:1] or super()._get_split_owner()

    def _get_split_request(self):
        """The พ.1 this slip's dialog acts for, with the group re-checked."""
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group(_REQUEST_GROUP):
            raise UserError(
                _("เฉพาะผู้ที่มีสิทธิ์จองงบประมาณแบบขอให้จัดหา (พ.1) เท่านั้นที่ดำเนินการขั้นนี้ได้")
            )
        request = self.sudo().purchase_request_ids[:1].with_env(self.env)
        if not request:
            raise UserError(_("ใบจอง %s ไม่ได้ผูกกับใบขอให้จัดหา") % self.display_name)
        return request

    def action_confirm_request_reserve(self):
        """ยืนยันจองงบประมาณ in the พ.1's dialog: reserve every row, then
        advance the พ.1 exactly as Reserve always did."""
        self.ensure_one()
        request = self._get_split_request()
        if self.state != "draft" or request.state not in (
            "to_verify_budget",
            "to_approve",
        ):
            raise UserError(_("ใบจอง %s ยืนยันจองงบประมาณในขั้นนี้ไม่ได้") % self.display_name)
        self._check_owner_budget_fields()
        self.sudo().action_reserve()
        request.message_post(
            body=_("Budget reserved: %s for amount %s") % (self.name, self.amount)
        )
        request.button_to_approve()
        # Closing the dialog reloads the พ.1 form it was opened from.
        return {"type": "ir.actions.act_window_close"}

    def action_save_request_split(self):
        """บันทึก: the save itself re-cut the reservation (the
        button saves the dialog first); just go back to the พ.1."""
        self.ensure_one()
        self._get_split_request()
        return {"type": "ir.actions.act_window_close"}

    def _action_open_request_dialog(self):
        """This slip in the พ.1's dialog view: header locked, split editable."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบจองงบประมาณ"),
            "res_model": "budget.commitment",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "purchase_request_budget_cross_charge.budget_commitment_request_dialog_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
            # Wide enough for the long budget-code names in the grid.
            "context": {"dialog_size": "extra-large"},
        }
