from odoo import api, fields, models

# Source states that no longer hold their commitment (AR: rejected,
# PR: rejected/cancelled).
DEAD_SOURCE_STATES = ("cancel", "cancelled", "rejected")


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # A commitment may itself be the source (ADR-0033).
    reference = fields.Reference(
        selection_add=[("budget.commitment", "ใบจองงบประมาณ")],
    )
    # Stored (ADR-0033): the reference itself when it is a commitment, else
    # the source's own. Follows the source in draft, fixed at submit. The loan
    # still never reserves on it (ADR-0025).
    budget_commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="ใบจองงบประมาณ",
        compute="_compute_budget_commitment_id",
        store=True,
        index=True,
        copy=False,
    )
    borrowing_headroom = fields.Monetary(
        string="วงเงินยืมคงเหลือ",
        compute="_compute_borrowing_headroom",
        compute_sudo=True,
        help="ยอดจองงบของใบจอง หักยอดยืมของสัญญาอื่นที่ส่งแล้วและยังไม่ยกเลิก"
        " (สัญญาที่ปิดแล้วยังนับ เพราะเงินออกไปแล้ว)",
    )
    exceeds_borrowing_headroom = fields.Boolean(
        compute="_compute_borrowing_headroom",
        compute_sudo=True,
        help="Technical flag read by the borrowing-headroom exception rule.",
    )
    is_budget_commitment_live = fields.Boolean(
        compute="_compute_borrowing_headroom",
        compute_sudo=True,
        help="Technical flag read by the live-commitment exception rule.",
    )
    is_commitment_held_by_source = fields.Boolean(
        compute="_compute_is_commitment_held_by_source",
        compute_sudo=True,
        help="Technical flag read by the cite-the-source exception rule.",
    )

    def _get_source_commitment(self):
        """The commitment the reference stands for, if it has one."""
        self.ensure_one()
        source = self.reference.sudo()
        if source._name == "budget.commitment":
            return source
        if source and "budget_commitment_id" in source._fields:
            return source.budget_commitment_id
        return self.env["budget.commitment"]

    @api.depends("reference")
    def _compute_budget_commitment_id(self):
        for rec in self:
            # Fixed once submitted; still filled on records that never had one
            # (the column's first compute on -u).
            if rec.state == "draft" or not rec.budget_commitment_id:
                rec.budget_commitment_id = (
                    rec._get_source_commitment() if rec.reference else False
                )

    def action_submit(self):
        # Re-read the source's commitment: it may have been re-pointed since
        # the reference was picked (ADR-0033).
        for rec in self.filtered(lambda r: r.state == "draft" and r.reference):
            rec.budget_commitment_id = rec._get_source_commitment()
        return super().action_submit()

    @api.model
    def _get_loans_on_commitment(self, commitment):
        """The loans counted in the commitment's borrowed amount: submitted
        and not cancelled (ADR-0033)."""
        return self.sudo().search(
            [
                ("budget_commitment_id", "=", commitment.id),
                ("state", "not in", ("draft", "cancel")),
            ]
        )

    @api.depends("budget_commitment_id", "loan_amount", "state")
    def _compute_borrowing_headroom(self):
        for rec in self:
            commitment = rec.budget_commitment_id
            rec.is_budget_commitment_live = bool(
                commitment and commitment.state in ("reserved", "partial")
            )
            if not commitment:
                rec.borrowing_headroom = 0.0
                rec.exceeds_borrowing_headroom = False
                continue
            others = rec._get_loans_on_commitment(commitment).filtered(
                lambda loan: loan.id != rec._origin.id
            )
            rec.borrowing_headroom = commitment.amount - sum(
                others.mapped("loan_amount")
            )
            rec.exceeds_borrowing_headroom = (
                rec.state != "cancel"
                and rec.currency_id.compare_amounts(
                    rec.loan_amount, rec.borrowing_headroom
                )
                > 0
            )

    @api.depends("reference")
    def _compute_is_commitment_held_by_source(self):
        """A commitment cited directly while a live source of another kind
        draws on it — the loan must cite that source (ADR-0033)."""
        selection = self._fields["reference"]._description_selection(self.env)
        for rec in self:
            commitment = rec.reference
            held = False
            if commitment and commitment._name == "budget.commitment":
                for model, _label in selection:
                    Source = self.env[model]
                    if model == "budget.commitment" or (
                        "budget_commitment_id" not in Source._fields
                    ):
                        continue
                    domain = [("budget_commitment_id", "=", commitment.id)]
                    if "state" in Source._fields:
                        domain.append(("state", "not in", DEAD_SOURCE_STATES))
                    if Source.search_count(domain, limit=1):
                        held = True
                        break
            rec.is_commitment_held_by_source = held

    def _get_reference_summary(self):
        summary = super()._get_reference_summary()
        commitment = self.reference.sudo()
        if commitment._name == "budget.commitment":
            summary.update(
                subject=(commitment.description or "").strip().split("\n")[0]
                or commitment.name,
                unit=commitment.department_analytic_id.display_name,
            )
        return summary

    def _prepare_account_payment_vals(self, payment_type):
        """Charge the voucher to the commitment header's dimensions — the
        commitment as a whole, not per line; accounting may still correct
        them on the voucher (ADR-0029)."""
        vals = super()._prepare_account_payment_vals(payment_type)
        distribution = self.sudo().budget_commitment_id.analytic_distribution
        if distribution:
            vals["analytic_distribution"] = distribution
        return vals
