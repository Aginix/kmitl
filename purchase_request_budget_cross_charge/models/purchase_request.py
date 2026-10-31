from odoo import _, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _reserve_new_budget(self):
        """From the form (context ``budget_reserve_dialog``), Reserve opens the
        ใบจองงบประมาณ itself as a dialog, where ถัวจ่าย codes are added before
        confirming (budget ADR-0020). Called from code (demo data, tests) it
        still reserves the one code directly."""
        if self.env.context.get("budget_reserve_dialog"):
            return self._prepare_reservation_slip()._action_open_request_dialog()
        return super()._reserve_new_budget()

    def _prepare_reservation_slip(self):
        """The draft ใบจองงบประมาณ behind the Reserve dialog (ADR-0020), built
        from — or refreshed to — this พ.1: ปีงบ, dimensions, Primary Code and
        วงเงิน = the พ.1 total. A slip left in draft by a closed dialog (or
        cancelled earlier) is reused, keeping its ถัว rows."""
        self.ensure_one()
        vals = self.sudo()._prepare_commitment_vals(
            sum(self.line_ids.mapped("estimated_cost")),
            self.activity_analytic_id.id,
            self.fund_analytic_id.id,
            self.department_analytic_id.id,
            self.source_analytic_id.id,
            self.name,
            f"Purchase Request: {self.name}",
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
        slip._sync_split_primary()
        return slip.with_env(self.env)

    def _action_open_request_dialog(self):
        return self.budget_commitment_id._action_open_request_dialog()

    def action_adjust_cross_charge(self):
        """ปรับถัวจ่าย: reopen the reserved slip's dialog while the พ.1 is
        reserved but not yet sent to e-Saraban (ADR-0020)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if not commitment.split_editable:
            raise UserError(
                _("ปรับถัวจ่ายได้เฉพาะคำขอที่จองงบแล้ว ยังไม่ส่งหนังสือ และยังไม่มีการใช้เงิน")
            )
        if not commitment.split_ids:
            commitment.sudo()._sync_split_primary()
        return commitment._action_open_request_dialog()
