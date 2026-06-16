# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class AddSubInstallmentWizard(models.TransientModel):
    _name = "add.sub.installment.wizard"
    _description = "Add Sub-Installments under a Parent Installment"

    parent_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="Parent Installment",
        required=True,
        readonly=True,
    )
    parent_installment = fields.Integer(
        related="parent_id.installment",
        readonly=True,
    )
    parent_amount = fields.Monetary(
        related="parent_id.amount",
        currency_field="currency_id",
        readonly=True,
    )
    parent_percent = fields.Float(
        related="parent_id.percent",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="parent_id.purchase_id.currency_id",
        readonly=True,
    )
    num_sub = fields.Integer(
        string="Number of Sub-Installments",
        default=2,
        required=True,
    )
    plan_date = fields.Date(
        string="Initial Plan Date",
        help="Plan date applied to every sub-installment. Edit per row afterwards.",
    )
    split_evenly = fields.Boolean(
        string="Split Evenly",
        default=True,
        help="Split parent's amount/percent evenly across sub-installments. "
             "Last sub takes the rounding remainder so the total matches the parent.",
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        parent_id = res.get("parent_id") or self.env.context.get("default_parent_id")
        if parent_id:
            parent = self.env["purchase.invoice.plan"].browse(parent_id)
            if not res.get("plan_date"):
                res["plan_date"] = parent.plan_date
        return res

    def action_create(self):
        self.ensure_one()
        parent = self.parent_id
        if parent.parent_id:
            raise UserError(
                _("A sub-installment cannot be split further.")
            )
        if parent.child_ids:
            raise UserError(
                _(
                    "Installment %s already has sub-installments. "
                    "Delete them first to re-split."
                )
                % parent.installment
            )
        if parent._no_edit():
            raise UserError(
                _(
                    "Installment %s is already locked (Work Acceptance or "
                    "invoice exists) and cannot be split."
                )
                % parent.installment
            )
        if self.num_sub < 2:
            raise UserError(_("Please choose at least 2 sub-installments."))

        Decimal = self.env["decimal.precision"]
        prec = Decimal.precision_get("Purchase Invoice Plan Percent")
        share = float_round(parent.percent / self.num_sub, prec)
        last_share = parent.percent - share * (self.num_sub - 1)

        vals_list = []
        for i in range(1, self.num_sub + 1):
            percent = last_share if i == self.num_sub else share
            vals_list.append(
                {
                    "purchase_id": parent.purchase_id.id,
                    "parent_id": parent.id,
                    "installment": parent.installment,
                    "sub_installment": i,
                    "invoice_type": parent.invoice_type,
                    "plan_date": self.plan_date or parent.plan_date,
                    "percent": percent if self.split_evenly else 0.0,
                }
            )
        self.env["purchase.invoice.plan"].create(vals_list)
        return {"type": "ir.actions.act_window_close"}
