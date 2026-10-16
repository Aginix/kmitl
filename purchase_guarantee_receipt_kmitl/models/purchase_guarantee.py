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

    # Cash first, then transfer. Never cheque: a cheque receipt is refused
    # without a cheque number, and that is a fact only the officer holds — the
    # guarantee does not record how the supplier paid. The two that are left
    # are exactly what the active guarantee forms cover (เงินสด/เงินโอน).
    _RECEIPT_PAYMENT_TYPE_PREFERENCE = ("cash", "transfer")

    def _guarantee_receipt_payment_method(self):
        """The channel the money is assumed to have come in by.

        A receipt cannot be created without one, so a default is proposed and
        the officer corrects it on the draft receipt, where the method and the
        payment type stay editable right up to posting — long before the
        remittance books anything.
        """
        self.ensure_one()
        Method = self.env["kmitl.payment.method"]
        for payment_type in self._RECEIPT_PAYMENT_TYPE_PREFERENCE:
            method = Method.search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("payment_type", "=", payment_type),
                ],
                order="sequence, name",
                limit=1,
            )
            if method:
                return method
        return Method

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
            # Stated outright as well as carried in the JSON. The field is a
            # stored compute over analytic_distribution, and a stored compute
            # is only filled after the INSERT — too late for a NOT NULL column.
            # The form gets away with it because its onchange fills the field
            # before saving; a programmatic create has to say it. Its inverse
            # then rebuilds the same distribution, keeping the other five
            # dimensions. receipt_kmitl's own test factory does the same.
            "department_analytic_id": self._guarantee_department_analytic().id,
            # Kept in step: an @api.constrains refuses a method whose own type
            # disagrees with the receipt's, and a transfer with no date.
            "payment_type": method.payment_type,
            "payment_method_id": method.id,
            "transfer_date": (
                self.date_guarantee_receive or fields.Date.context_today(self)
                if method.payment_type == "transfer"
                else False
            ),
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
        # Monetary fields ignore a view-level required="1" in Odoo 16, so a
        # guarantee can legitimately be saved with no amount. Caught here
        # rather than letting kmitl.receipt refuse a zero total, which names a
        # document the officer never opened.
        if self.currency_id.is_zero(self.amount) or self.amount < 0:
            raise UserError(
                _("Fill in the guarantee amount before issuing its receipt.")
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
                    "No cash or transfer receipt method is configured for this "
                    "company. Add one in Receipts > Configuration > Payment "
                    "Methods."
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
