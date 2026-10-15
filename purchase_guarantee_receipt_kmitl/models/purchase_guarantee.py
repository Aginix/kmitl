# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    receipt_ids = fields.One2many(
        comodel_name="kmitl.receipt",
        inverse_name="purchase_guarantee_id",
        string="Guarantee Receipts",
    )
    receipt_count = fields.Integer(compute="_compute_receipt_count")
    has_active_receipt = fields.Boolean(compute="_compute_has_active_receipt")
    is_monetary_guarantee = fields.Boolean(
        related="guarantee_type_id.is_monetary",
        string="Received as Money",
    )

    @api.depends("receipt_ids")
    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)

    @api.depends("receipt_ids.state")
    def _compute_has_active_receipt(self):
        for rec in self:
            rec.has_active_receipt = any(
                r.state != "cancelled" for r in rec.receipt_ids
            )

    @api.depends("receipt_ids.state", "receipt_ids.amount_total")
    def _compute_amount_received(self):
        """Money in is what the guarantee receipt booked.

        Replaces the upstream compute over ``invoice_ids``: KMITL never raises
        the customer invoice that field counts, so it always read zero.
        """
        for rec in self:
            rec.amount_received = sum(
                rec.receipt_ids.filtered(lambda r: r.state == "done").mapped(
                    "amount_total"
                )
            )

    def _guarantee_department_analytic(self):
        """The departments dimension the receipt will be filed under.

        Keyed on ``plan_id.code`` to match what actually populates
        ``kmitl.receipt.department_analytic_id`` (see
        ``account_analytic_kmitl``), so this guard and that compute cannot
        disagree.
        """
        self.ensure_one()
        accounts = self.env["account.analytic.account"].browse(
            [int(account_id) for account_id in (self.analytic_distribution or {})]
        )
        return accounts.filtered(lambda a: a.plan_id.code == "departments")[:1]

    def _guarantee_receipt_payment_method(self):
        """The channel the money is assumed to have come in by.

        A receipt cannot be created without one, and the guarantee does not
        record how the supplier paid — so the lowest-sequence method is proposed
        and the officer corrects it on the draft receipt, where both it and the
        payment type stay editable right up to posting.
        """
        self.ensure_one()
        return self.env["kmitl.payment.method"].search(
            [("company_id", "=", self.company_id.id)],
            order="sequence, name",
            limit=1,
        )

    def _prepare_guarantee_receipt_vals(self):
        self.ensure_one()
        product = self.env.ref(
            "purchase_guarantee_receipt_kmitl.product_guarantee"
        ).product_variant_id
        method = self._guarantee_receipt_payment_method()
        return {
            "receipt_kind": "guarantee",
            "purchase_guarantee_id": self.id,
            "partner_id": self.partner_id.id,
            "date": self.date_guarantee_receive or fields.Date.context_today(self),
            "description": self.guarantee_method_id.name,
            # Kept in step: an @api.constrains refuses a method whose own type
            # disagrees with the receipt's.
            "payment_type": method.payment_type,
            "payment_method_id": method.id,
            "analytic_distribution": self.analytic_distribution,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": self.guarantee_method_id.name,
                        # The method's account wins over the product's: the
                        # product is one generic placeholder for every kind of
                        # guarantee, the account is configured per kind.
                        "account_id": self.guarantee_method_id.account_id.id,
                        "quantity": 1,
                        "price_unit": self.amount,
                    },
                )
            ],
        }

    def action_create_receipt(self):
        self.ensure_one()

        if not self.is_monetary_guarantee:
            raise UserError(
                _(
                    "Guarantees held as '%s' are not received as money, so no "
                    "receipt is issued."
                )
                % self.guarantee_type_id.name
            )
        if self.has_active_receipt:
            raise UserError(
                _(
                    "This guarantee already has a receipt. A second one cannot "
                    "be issued."
                )
            )
        if not self.guarantee_method_id.account_id:
            raise UserError(
                _(
                    "Guarantee method '%s' has no account yet. Set it in "
                    "Purchase > Configuration > Guarantee Method."
                )
                % self.guarantee_method_id.name
            )
        if not self._guarantee_receipt_payment_method():
            raise UserError(
                _(
                    "No receipt payment method is configured for this company. "
                    "Add one in Receipts > Configuration > Payment Methods."
                )
            )
        if not self._guarantee_department_analytic():
            raise UserError(
                _(
                    "This guarantee carries no department dimension, so no "
                    "receipt can be issued for it. Add one on the source "
                    "document (purchase request / purchase order) first."
                )
            )

        receipt = self.env["kmitl.receipt"].create(
            self._prepare_guarantee_receipt_vals()
        )
        self.button_lock()

        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.receipt",
            "res_id": receipt.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_receipts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "receipt_kmitl.action_receipt_kmitl"
        )
        if self.receipt_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.receipt_ids.id
        else:
            action["domain"] = [("id", "in", self.receipt_ids.ids)]
        action["context"] = {}
        return action
