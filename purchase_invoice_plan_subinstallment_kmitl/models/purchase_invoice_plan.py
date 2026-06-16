# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class PurchaseInvoicePlan(models.Model):
    _inherit = "purchase.invoice.plan"
    _order = "installment, sub_installment, id"

    parent_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="Parent Installment",
        index=True,
        ondelete="cascade",
        copy=False,
    )
    child_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="parent_id",
        string="Sub-Installments",
        copy=False,
    )
    sub_installment = fields.Integer(
        string="Sub Installment",
        default=0,
        help="0 for root installment; >=1 for the sequence of a sub-installment.",
    )
    has_children = fields.Boolean(
        compute="_compute_hierarchy_flags",
        store=False,
    )
    is_sub = fields.Boolean(
        compute="_compute_hierarchy_flags",
        store=False,
    )
    installment_display = fields.Char(
        string="Installment",
        compute="_compute_installment_display",
        store=False,
    )

    @api.depends("child_ids", "parent_id")
    def _compute_hierarchy_flags(self):
        for rec in self:
            rec.has_children = bool(rec.child_ids)
            rec.is_sub = bool(rec.parent_id)

    @api.depends("installment", "sub_installment", "parent_id.installment")
    def _compute_installment_display(self):
        for rec in self:
            if rec.parent_id:
                rec.installment_display = "    ↳ %s.%s" % (
                    rec.parent_id.installment,
                    rec.sub_installment,
                )
            else:
                rec.installment_display = str(rec.installment or "")

    # -- helpers ----------------------------------------------------------

    def _sibling_scope(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id.child_ids
        return self.purchase_id.invoice_plan_ids.filtered(
            lambda l: l.invoice_type == "installment" and not l.parent_id
        )

    def _scope_total(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id.amount
        return self.purchase_id._origin.amount_total

    def _scope_percent(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id.percent
        return 100.0

    # -- compute / inverse overrides --------------------------------------

    @api.depends("percent")
    def _compute_amount(self):
        for rec in self:
            amount_total = rec.purchase_id._origin.amount_total
            if rec.invoiced:
                rec.amount = rec.amount_invoiced
                rec.percent = (
                    rec.amount / amount_total * 100 if amount_total else 0
                )
                continue
            if rec.last and not rec.child_ids:
                scope = rec._sibling_scope()
                scope_total = rec._scope_total()
                prev_amount = sum((scope - rec).mapped("amount"))
                rec.amount = scope_total - prev_amount
                continue
            rec.amount = rec.percent * amount_total / 100

    @api.onchange("amount", "percent")
    def _inverse_amount(self):
        for rec in self:
            # Parent container — derived from children, no inverse.
            if rec.child_ids:
                continue
            amount_total = rec.purchase_id.amount_total
            if amount_total != 0:
                if rec.last:
                    scope = rec._sibling_scope()
                    scope_percent = rec._scope_percent()
                    prev_percent = sum((scope - rec).mapped("percent"))
                    rec.percent = scope_percent - prev_percent
                    continue
                rec.percent = rec.amount / amount_total * 100
                continue
            rec.percent = 0

    def _compute_last(self):
        for rec in self:
            siblings = rec._sibling_scope()
            if rec.parent_id:
                max_sub = max(siblings.mapped("sub_installment") or [0])
                rec.last = rec.sub_installment == max_sub
            else:
                max_inst = max(siblings.mapped("installment") or [0])
                rec.last = rec.installment == max_inst

    @api.depends("purchase_id.state", "purchase_id.invoice_plan_ids.invoiced")
    def _compute_to_invoice(self):
        """Next-to-invoice is the first non-invoiced leaf in (installment,
        sub_installment) order. Parents with children are not invoiceable.
        """
        for rec in self:
            rec.to_invoice = False
        leaves = self.filtered(lambda l: not l.child_ids)
        for rec in leaves.sorted(lambda l: (l.installment, l.sub_installment, l.id)):
            if rec.purchase_id.state != "purchase":
                continue
            if not rec.invoiced:
                rec.to_invoice = True
                break

    def _no_edit(self):
        no_edit = super()._no_edit()
        return no_edit or bool(self.child_ids)

    # -- constraints ------------------------------------------------------

    @api.constrains("parent_id")
    def _check_nesting_depth(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id:
                raise ValidationError(
                    _("Sub-installments cannot be nested further.")
                )

    @api.constrains("parent_id", "percent", "child_ids")
    def _check_sub_percent_within_parent(self):
        Decimal = self.env["decimal.precision"]
        prec = Decimal.precision_get("Purchase Invoice Plan Percent")
        for rec in self:
            parent = rec.parent_id
            if not parent:
                continue
            total_children = sum(parent.child_ids.mapped("percent"))
            if float_compare(total_children, parent.percent, prec) > 0:
                raise ValidationError(
                    _(
                        "Sub-installments under installment %(parent)s sum to "
                        "%(children)s%% which exceeds the parent's %(parent_percent)s%%."
                    )
                    % {
                        "parent": parent.installment,
                        "children": total_children,
                        "parent_percent": parent.percent,
                    }
                )

    # -- UI entry point ---------------------------------------------------

    def action_open_add_sub_wizard(self):
        self.ensure_one()
        if self.parent_id:
            raise ValidationError(
                _("A sub-installment cannot be split further.")
            )
        if self._no_edit() and not self.child_ids:
            raise ValidationError(
                _(
                    "Installment %s is already locked (Work Acceptance or "
                    "invoice exists) and cannot be split."
                )
                % self.installment
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Split into Sub-Installments"),
            "res_model": "add.sub.installment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_parent_id": self.id,
            },
        }
