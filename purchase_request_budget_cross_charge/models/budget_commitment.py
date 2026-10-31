from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

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

    # What the พ.1 dialog may change: the split, the primary code and the
    # dimensions. The วงเงิน stays the พ.1 total.
    _REQUEST_DIALOG_FIELDS = {
        "split_ids",
        "account_id",
        "analytic_distribution",
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    }

    def write(self, vals):
        """ผู้จองงบประมาณ พ.1 holds write on the slip for its dialog fields
        only, and only inside the พ.1's windows — no Budget User rights
        (ADR-0020). A changed code or dimension is copied back to the พ.1."""
        if not self.env.su and not self.env.user.has_group("budget.group_budget_user"):
            if set(vals) - self._REQUEST_DIALOG_FIELDS:
                raise AccessError(
                    _("แก้ไขได้เฉพาะรหัสงบ มิติ และรายการจองงบประมาณ (ถัวจ่าย) ของใบจอง")
                )
            for record in self:
                # Only a พ.1's own slip: the group must not reach the split of
                # a standalone draft slip it happens to see.
                if not (record.split_editable and record.sudo().purchase_request_ids):
                    raise UserError(
                        _("ใบจอง %s แก้ไขรายการจองงบประมาณ (ถัวจ่าย) ในขั้นนี้ไม่ได้")
                        % record.display_name
                    )
        # Clearing the code or a dimension is refused up front, before the
        # re-cut reports it as a budget shortfall.
        cleared = [
            f for f in self._REQUEST_REQUIRED_FIELDS if f in vals and not vals[f]
        ]
        if cleared and self.sudo().purchase_request_ids:
            labels = dict(self._request_required_labels())
            raise UserError(
                _("กรุณาระบุข้อมูลงบประมาณให้ครบ: %s")
                % ", ".join(labels[f] for f in cleared)
            )
        res = super().write(vals)
        if (
            not self.env.context.get("budget_split_batch")
            and not self.env.context.get("budget_slip_from_request")
            and (self._REQUEST_DIALOG_FIELDS - {"split_ids"}) & set(vals)
        ):
            self._check_request_budget_fields()
            self._sync_request_from_slip()
        return res

    _REQUEST_REQUIRED_FIELDS = (
        "account_id",
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    def _request_required_labels(self):
        return [
            ("account_id", _("รหัสงบประมาณ")),
            ("department_analytic_id", _("ส่วนงาน")),
            ("source_analytic_id", _("แหล่งเงิน")),
            ("fund_analytic_id", _("กองทุน")),
            ("activity_analytic_id", _("กิจกรรม")),
        ]

    def _check_request_budget_fields(self):
        """A พ.1's slip needs its code and all four dimensions, as Reserve on
        the พ.1 demands."""
        for record in self.filtered(lambda r: r.sudo().purchase_request_ids):
            missing = [
                label
                for fname, label in self._request_required_labels()
                if not record[fname]
            ]
            if missing:
                raise UserError(_("กรุณาระบุข้อมูลงบประมาณให้ครบ: %s") % ", ".join(missing))

    def _sync_request_from_slip(self):
        """Copy the slip's primary code and dimensions back to its พ.1 (and the
        พ.1 lines), so the พ.1, its product and its letter follow the slip."""
        for record in self.sudo():
            request = record.purchase_request_ids[:1]
            if not request or not record._is_split_capable():
                continue
            vals = {}
            if request.budget_account_id != record.account_id:
                vals["budget_account_id"] = record.account_id.id
            distribution = record.analytic_distribution or False
            if (request.analytic_distribution or False) != distribution:
                vals["analytic_distribution"] = distribution
            if not vals:
                continue
            request.write(vals)
            if "analytic_distribution" in vals and request.line_ids:
                request.line_ids.write({"analytic_distribution": distribution})
            request.message_post(
                body=_("เปลี่ยนรหัสงบประมาณ/มิติตามใบจอง %s") % record.display_name,
                subtype_xmlid="mail.mt_note",
            )

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
        self._check_request_budget_fields()
        self.sudo().action_reserve()
        request.message_post(
            body=_("Budget reserved: %s for amount %s") % (self.name, self.amount)
        )
        request.button_to_approve()
        # Closing the dialog reloads the พ.1 form it was opened from.
        return {"type": "ir.actions.act_window_close"}

    def action_save_request_split(self):
        """บันทึกการถัวจ่าย: the save itself re-cut the reservation (the
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
