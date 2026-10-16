from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        ondelete="set null",
        index=True,
        copy=False,
        tracking=True,
    )

    reference = fields.Reference(
        selection_add=[('approval.request', 'Approval Request')],
        ondelete={'approval.request': 'set null'},
    )

    # The requester's evidence, shown read-only on every ใบขอเบิก of the request
    # instead of being copied onto each (ADR-0009).
    approval_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="หลักฐานจากใบขออนุมัติ",
        compute="_compute_approval_attachment_ids",
    )

    @api.depends("approval_request_id")
    def _compute_approval_attachment_ids(self):
        Attachment = self.env["ir.attachment"]
        for rec in self:
            # sudo to reach the request, then keep only files the viewer may
            # open — the widget reads them as the user, and an attachment of a
            # request they cannot read would AccessError the whole form.
            ids = rec.approval_request_id.sudo().disbursement_attachment_ids.ids
            rec.approval_attachment_ids = Attachment._filter_attachment_access(ids)

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env["approval.request"].browse(
            [v["approval_request_id"] for v in vals_list if v.get("approval_request_id")]
        )
        if any(r.state != "to_disburse" for r in requests.sudo()):
            raise UserError(
                _("สร้างใบขอเบิกได้เฉพาะคำขออนุมัติสถานะ 'รอการเงินตรวจสอบ/ส่งเบิก'")
            )
        return super().create(vals_list)

    def _check_approval_billing_cap(self):
        """Block a ใบขอเบิก that would push the request's non-cancelled
        ใบขอเบิก past its recorded actual total (ADR-0009)."""
        for rec in self.filtered("approval_request_id"):
            request = rec.approval_request_id.sudo()
            if request.currency_id.compare_amounts(
                request.disbursed_amount, request.total_actual_amount
            ) > 0:
                raise UserError(
                    _(
                        "ยอดรวมใบขอเบิกของ %(request)s (%(disbursed)s) เกินยอด"
                        "ค่าใช้จ่ายจริง (%(actual)s)"
                    )
                    % {
                        "request": request.name,
                        "disbursed": request.disbursed_amount,
                        "actual": request.total_actual_amount,
                    }
                )

    def action_submit(self):
        self._check_approval_billing_cap()
        return super().action_submit()

    def action_resubmit_verification(self):
        # A returned ใบขอเบิก skips action_submit on its way back to verification.
        self._check_approval_billing_cap()
        return super().action_resubmit_verification()

    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(
                _("No Approval Request linked to this request.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
