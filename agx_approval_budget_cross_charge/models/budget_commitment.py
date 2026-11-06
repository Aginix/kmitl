from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    approval_request_ids = fields.One2many(
        comodel_name="approval.request",
        inverse_name="budget_commitment_id",
        string="คำขออนุมัติ",
    )
    approval_account_domain = fields.Binary(
        compute="_compute_approval_account_domain",
        help="Codes the Primary Code may be in the request's dialog: the "
        "request's own selectable codes (approval_ok, category pin).",
    )

    # --- ถัวจ่าย on an approval request's slip (agx_approval ADR-0011) ---

    def _get_approval_owner(self):
        """The request that reserved this slip itself — not one drawing it."""
        self.ensure_one()
        return self.sudo().approval_request_ids.filtered(
            lambda r: not r.reservation_commitment_id
        )[:1]

    def _get_split_owner(self):
        return self._get_approval_owner() or super()._get_split_owner()

    def _split_candidate_domain(self):
        """A ถัว code of a request must be approval-eligible too (ADR-0011)."""
        domain = super()._split_candidate_domain()
        if self._get_approval_owner():
            domain = domain + [("approval_ok", "=", True)]
        return domain

    @api.depends("approval_request_ids.state")
    def _compute_split_editable(self):
        """A request's slip has two windows: draft while the request waits for
        ยืนยันงบประมาณ, and reserved-but-unused while it waits to be sent or
        is back from e-Saraban (ตีกลับ/ดึงกลับ)."""
        super()._compute_split_editable()
        for record in self:
            request = record._get_approval_owner()
            if request and record._is_split_capable():
                record.split_editable = record._is_approval_split_window(request)

    def _is_approval_split_window(self, request):
        self.ensure_one()
        if self.state == "draft":
            return request.state == "to_commit"
        returned_by_sarabun = (
            request.state == "returned"
            and "sarabun_state" in request._fields
            and request.sarabun_state == "returned"
        )
        return (
            self.state == "reserved"
            and (request.state == "to_send" or returned_by_sarabun)
            and not self.line_ids.filtered(
                lambda line: (
                    line.state == "posted"
                    and (line.move_type != "reserve" or line.is_return)
                )
            )
        )

    @api.depends("account_id")
    def _compute_approval_account_domain(self):
        for record in self:
            request = record._get_approval_owner()
            record.approval_account_domain = (
                request._reservation_account_domain() if request else False
            )

    def write(self, vals):
        """The Primary Code of a request's slip stays one the request may
        select (approval_ok, category pin)."""
        if vals.get("account_id"):
            for record in self:
                request = record._get_approval_owner()
                if request and not self.env["budget.account"].sudo().search_count(
                    request._reservation_account_domain()
                    + [("id", "=", vals["account_id"])]
                ):
                    raise UserError(
                        _("รหัสงบประมาณนี้ใช้กับคำขออนุมัติ %s ไม่ได้") % request.display_name
                    )
        return super().write(vals)

    def _get_split_approval_request(self):
        """The request this slip's dialog acts for, with the group re-checked."""
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group(
            "agx_approval.group_approval_budget_commit"
        ):
            raise UserError(_("เฉพาะผู้ยืนยันงบประมาณของคำขออนุมัติเท่านั้นที่ดำเนินการขั้นนี้ได้"))
        request = self._get_approval_owner().with_env(self.env)
        if not request:
            raise UserError(_("ใบจอง %s ไม่ได้ผูกกับคำขออนุมัติ") % self.display_name)
        return request

    def action_confirm_approval_reserve(self):
        """ยืนยันจองงบประมาณ in the request's dialog: reserve every row, then
        advance the request exactly as ยืนยันงบประมาณ always did."""
        self.ensure_one()
        request = self._get_split_approval_request()
        if self.state != "draft" or request.state != "to_commit":
            raise UserError(_("ใบจอง %s ยืนยันจองงบประมาณในขั้นนี้ไม่ได้") % self.display_name)
        self._check_owner_budget_fields()
        self.sudo().action_reserve()
        request.message_post(
            body=_("Budget reserved: %s for amount %s") % (self.name, self.amount)
        )
        request._advance_after_reserved()
        # Closing the dialog reloads the request form it was opened from.
        return {"type": "ir.actions.act_window_close"}

    def action_save_approval_split(self):
        """บันทึก: the save itself re-cut the reservation (the button saves
        the dialog first); just go back to the request."""
        self.ensure_one()
        self._get_split_approval_request()
        return {"type": "ir.actions.act_window_close"}

    def _action_open_approval_dialog(self):
        """This slip in the request's dialog view: วงเงิน locked, split,
        Primary Code and dimensions editable in the windows."""
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
                        "agx_approval_budget_cross_charge.budget_commitment_approval_dialog_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
            # Wide enough for the long budget-code names in the grid.
            "context": {"dialog_size": "extra-large"},
        }
