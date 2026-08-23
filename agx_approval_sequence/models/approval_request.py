from odoo import _, api, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    @api.model
    def _mint_name_on_create(self):
        """The number now encodes the ปีงบประมาณ (AR/{yr}/{number}), which is only
        settled once the user commits to a fiscal year — so it is minted at
        submission (action_to_verify), not at creation."""
        return False

    def action_to_verify(self):
        result = super().action_to_verify()
        if result is True:
            self._ensure_approval_request_number()
        return result

    def _ensure_approval_request_number(self):
        """Issue the request's running number once, on first submission.
        Idempotent — a later reset-to-draft (or ตีกลับ/ดึงกลับ) keeps the number,
        never re-issues it. Stamped with the request's fiscal year (not today) by
        drawing the sequence on the fiscal year's end date, so the number always
        reads as its ปีงบประมาณ — see write() below for the matching guard against
        the fiscal year drifting afterwards."""
        self.ensure_one()
        if self.name and self.name != "/":
            return
        fiscal_date = self.account_fiscal_year_id.date_to
        self.name = self.env["ir.sequence"].with_context(
            ir_sequence_date=fiscal_date
        ).next_by_code(
            "approval.request",
            sequence_date=fiscal_date,
        ) or "/"

    def write(self, vals):
        """Freeze the ปีงบประมาณ for good once the request's number exists — the
        number is stamped with account_fiscal_year_id and must never drift.
        Without this guard, action_draft (reset to draft) or a Sarabun
        ตีกลับ/ดึงกลับ reopen the field for editing while the old number still
        stands, silently desyncing the two."""
        if "account_fiscal_year_id" in vals:
            for rec in self:
                if (
                    rec.name
                    and rec.name != "/"
                    and rec.account_fiscal_year_id.id != vals["account_fiscal_year_id"]
                ):
                    raise UserError(
                        _(
                            "ไม่สามารถเปลี่ยนปีงบประมาณได้ "
                            "เนื่องจากคำขอมีเลขที่ออกแล้ว (%s)"
                        )
                        % rec.name
                    )
        return super().write(vals)
