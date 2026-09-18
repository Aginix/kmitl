# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseContractInvoicePlan(models.Model):
    _name = "purchase.contract.invoice.plan"
    _description = "Purchase Contract Invoice Plan (งวดงาน snapshot)"
    _order = "installment"

    contract_id = fields.Many2one(
        "purchase.contract",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Mirror of purchase.invoice.plan
    installment = fields.Integer(string="Installment", required=True)
    duration_days = fields.Integer(string="Duration (Days)", default=0)
    plan_date = fields.Date(string="Planned Date")
    amount = fields.Monetary(string="Amount", required=True)
    percent = fields.Float(string="Percent")

    # Reference to the live งวด this snapshot was created from. When None,
    # this is a newly-added งวด during a revision.
    source_invoice_plan_id = fields.Many2one(
        "purchase.invoice.plan",
        ondelete="set null",
        help="Original งวด this snapshot was cloned from, if any.",
    )

    is_frozen = fields.Boolean(
        compute="_compute_is_frozen",
        store=True,
        help="True if the source งวด has an existing disbursement.request. "
        "Frozen rows are readonly and their amounts cannot change on this revision.",
    )

    currency_id = fields.Many2one(
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("source_invoice_plan_id")
    def _compute_is_frozen(self):
        """A งวด is frozen when its source has a disbursement.request created against
        the parent PO. We approximate this via the presence of any
        disbursement.request whose purchase_id points to our PO — the strict
        per-งวด link will be tightened in a follow-up if the disbursement model
        gains an installment_id field."""
        Disbursement = self.env["disbursement.request"].sudo()
        for rec in self:
            source = rec.source_invoice_plan_id
            if not source:
                rec.is_frozen = False
                continue
            # Any disbursement on this PO whose reference matches this งวด's
            # sequence / purchase_id is treated as freezing it. The
            # disbursement.request model is expected to carry `purchase_id`
            # (see purchase_order_disbursement); refine later once งวด linkage
            # is explicit.
            po = source.purchase_id
            count = Disbursement.search_count(
                [("purchase_id", "=", po.id)]
            )
            rec.is_frozen = bool(count) and source.invoiced
