from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # Who may edit this request's slip in its dialog (agx_approval ADR-0011).
    _cross_charge_group = "agx_approval.group_approval_budget_commit"

    can_adjust_cross_charge = fields.Boolean(
        compute="_compute_can_adjust_cross_charge",
        help="แก้ไขใบจอง: the reserved slip is in one of its edit windows.",
    )

    @api.depends("state", "budget_commitment_id.state")
    def _compute_can_adjust_cross_charge(self):
        for rec in self:
            slip = rec.budget_commitment_id
            rec.can_adjust_cross_charge = bool(
                slip.state == "reserved"
                and not rec.reservation_commitment_id
                and slip.split_editable
            )

    def _reserve_new_budget(self):
        """From the form (context ``budget_reserve_dialog``), ยืนยันงบประมาณ
        opens the ใบจองงบประมาณ itself as a dialog, where ถัวจ่าย codes are
        added before confirming (ADR-0011). Called from code it still
        reserves the one code directly."""
        if self.env.context.get("budget_reserve_dialog"):
            return self._prepare_reservation_slip()._action_open_approval_dialog()
        return super()._reserve_new_budget()

    def _prepare_reservation_slip(self):
        """The draft ใบจองงบประมาณ behind the dialog, built from — or refreshed
        to — this request: ปีงบ, dimensions, Primary Code and วงเงิน = the
        request total. A slip left in draft by a closed dialog (or cancelled
        by ดึงกลับ) is reused, keeping its ถัว rows."""
        self.ensure_one()
        vals = self.sudo()._prepare_commitment_vals(
            sum(self.line_ids.mapped("total_amount")),
            self.activity_analytic_id.id,
            self.fund_analytic_id.id,
            self.department_analytic_id.id,
            self.source_analytic_id.id,
            self.name,
            f"Approval Request: {self.name}",
            self.budget_account_id,
            account_fiscal_year_id=self.account_fiscal_year_id.id,
            **self._get_budget_commitment_extra_kwargs(),
        )
        vals.pop("line_ids")
        slip = self.sudo().budget_commitment_id
        if slip.state == "cancel":
            slip.action_reset_to_draft()
        if slip.state == "draft":
            vals.pop("company_id", None)
            slip.with_context(budget_slip_from_request=True).write(vals)
        else:
            slip = self.env["budget.commitment"].sudo().create(vals)
            self.sudo().budget_commitment_id = slip
            self.sudo()._log_budget_commitment_linked()
        slip._sync_split_primary()
        return slip.with_env(self.env)

    def action_adjust_cross_charge(self):
        """แก้ไขใบจอง: reopen the reserved slip's dialog while the request is
        reserved, unused and not circulating (ADR-0011)."""
        self.ensure_one()
        if not self.can_adjust_cross_charge:
            raise UserError(
                _(
                    "แก้ไขใบจองได้เฉพาะคำขอที่จองงบแล้ว ยังไม่ส่งหนังสือ (หรือถูกตีกลับ) และยังไม่มีการใช้เงิน"
                )
            )
        commitment = self.budget_commitment_id
        if not commitment.split_ids:
            commitment.sudo()._sync_split_primary()
        return commitment._action_open_approval_dialog()

    def _cross_charge_split_lines(self):
        """The letter's รหัสงบประมาณ rows: every code of a ถัวจ่าย reservation
        with its amount, primary first; empty for a single code."""
        self.ensure_one()
        # sudo: the letter's readers hold no access to the split rows.
        splits = self.budget_commitment_id.sudo().split_ids
        if len(splits) < 2:
            return []
        currency = self.budget_commitment_id.currency_id
        return [
            {
                "primary": split.is_primary,
                "account": split.account_id.display_name,
                "amount": formatLang(self.env, split.amount, currency_obj=currency),
            }
            for split in splits
        ]
