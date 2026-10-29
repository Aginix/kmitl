from odoo import api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # The loan holds no commitment of its own (ADR-0025): it reaches its
    # source's, under sudo — the borrower, or the endorser a borrowing rule
    # runs as, usually cannot read the source (ADR-0029/0030).
    budget_commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="ใบจองงบประมาณ",
        compute="_compute_borrowing_headroom",
        compute_sudo=True,
    )
    borrowing_headroom = fields.Monetary(
        string="วงเงินยืมคงเหลือ",
        compute="_compute_borrowing_headroom",
        compute_sudo=True,
        help="ยอดจองงบของใบจองต้นเรื่อง หักสัญญายืมเงินอื่นที่ยังไม่ยกเลิก"
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

    def _get_source_commitment(self):
        """The commitment of the source document, if its model has one."""
        self.ensure_one()
        source = self.reference.sudo()
        if source and "budget_commitment_id" in source._fields:
            return source.budget_commitment_id
        return self.env["budget.commitment"]

    @api.model
    def _get_loans_on_commitment(self, commitment):
        """Every non-cancelled loan whose source draws on `commitment`, across
        all source models — several sources could share one commitment."""
        references = []
        selection = self._fields["reference"]._description_selection(self.env)
        for model, _label in selection:
            Source = self.env[model].sudo().with_context(active_test=False)
            if "budget_commitment_id" not in Source._fields:
                continue
            references += [
                "%s,%s" % (model, source_id)
                for source_id in Source.search(
                    [("budget_commitment_id", "=", commitment.id)]
                ).ids
            ]
        if not references:
            return self.browse()
        return self.sudo().search(
            [("reference", "in", references), ("state", "!=", "cancel")]
        )

    @api.depends("reference", "loan_amount", "state")
    def _compute_borrowing_headroom(self):
        for rec in self:
            commitment = rec._get_source_commitment() if rec.reference else False
            rec.budget_commitment_id = commitment
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

    def _prepare_account_payment_vals(self, payment_type):
        """Charge the voucher to the commitment header's dimensions — the
        commitment as a whole, not per line; accounting may still correct
        them on the voucher (ADR-0029)."""
        vals = super()._prepare_account_payment_vals(payment_type)
        distribution = self.sudo().budget_commitment_id.analytic_distribution
        if distribution:
            vals["analytic_distribution"] = distribution
        return vals
