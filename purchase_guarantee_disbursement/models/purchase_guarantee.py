# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# The request has reached the payee once the finance office has confirmed the
# Hand-over; `cleared` is the accounting office's later step on the same money.
RETURNED_STATES = ("paid", "cleared")


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="purchase_guarantee_id",
        string="Return Requests",
    )
    disbursement_count = fields.Integer(compute="_compute_disbursement_count")
    has_active_return = fields.Boolean(compute="_compute_has_active_return")
    # Upstream types this by hand; here the paid return request knows it.
    date_return = fields.Date(
        compute="_compute_date_return",
        store=True,
        readonly=False,
    )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_count(self):
        for rec in self:
            rec.disbursement_count = len(rec.disbursement_request_ids)

    @api.depends("disbursement_request_ids.state")
    def _compute_has_active_return(self):
        for rec in self:
            rec.has_active_return = any(
                dr.state != "cancel" for dr in rec.disbursement_request_ids
            )

    def _returned_disbursements(self):
        self.ensure_one()
        return self.disbursement_request_ids.filtered(
            lambda dr: dr.state in RETURNED_STATES
        )

    @api.depends("disbursement_request_ids.state",
                 "disbursement_request_ids.amount_total")
    def _compute_amount_returned(self):
        """Money out is what a paid return request actually sent.

        Replaces the upstream compute over ``bill_ids``: KMITL never raises the
        vendor bill that field counts, so it always read zero.
        """
        for rec in self:
            rec.amount_returned = sum(
                rec._returned_disbursements().mapped("amount_total")
            )

    @api.depends("disbursement_request_ids.state",
                 "disbursement_request_ids.payment_ids.date",
                 "disbursement_request_ids.payment_ids.state")
    def _compute_date_return(self):
        """When the deposit went back — the last voucher's date.

        Stored and still editable: the upstream field was typed by hand, and a
        guarantee returned before this module existed keeps whatever was typed
        until a return request moves.
        """
        for rec in self:
            dates = (
                rec._returned_disbursements()
                .payment_ids.filtered(lambda p: p.state != "cancel")
                .mapped("date")
            )
            if dates:
                rec.date_return = max(dates)

    def _prepare_return_disbursement_vals(self):
        self.ensure_one()
        product = self.env.ref(
            "purchase_guarantee_receipt_kmitl.product_guarantee"
        ).product_variant_id
        return {
            "purchase_guarantee_id": self.id,
            "partner_type_id": self.env["disbursement.request"]
            ._get_payee_type(self.partner_id)
            .id,
            "analytic_distribution": self.analytic_distribution,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": _("Return of %s") % self.name,
                        # The method's account wins over the product's: the
                        # product is one generic placeholder, the account is
                        # configured per kind of guarantee.
                        "account_id": self.guarantee_method_id.account_id.id,
                        "partner_id": self.partner_id.id,
                        "quantity": 1,
                        "price_unit": self.amount,
                        "analytic_distribution": self.analytic_distribution,
                    },
                )
            ],
        }

    def action_create_return_disbursement(self):
        self.ensure_one()

        if not self.is_monetary_guarantee:
            raise UserError(
                _(
                    "Guarantees held as '%s' are not received as money, so "
                    "there is nothing to return."
                )
                % self.guarantee_type_id.name
            )
        if self.has_active_return:
            raise UserError(
                _(
                    "This guarantee already has a return request. A second one "
                    "cannot be raised."
                )
            )
        # Monetary fields ignore a view-level required="1" in Odoo 16, so a
        # guarantee can be saved with no amount — and a request for nothing
        # would walk the whole approval chain before anyone noticed.
        if self.currency_id.is_zero(self.amount) or self.amount < 0:
            raise UserError(
                _("Fill in the guarantee amount before raising its return.")
            )
        if not self.guarantee_method_id.account_id:
            raise UserError(
                _(
                    "Guarantee method '%s' has no account yet. Set it in "
                    "Purchase > Configuration > Guarantee Method."
                )
                % self.guarantee_method_id.name
            )

        request = self.env["disbursement.request"].create(
            self._prepare_return_disbursement_vals()
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_disbursements(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "disbursement.action_disbursement_request"
        )
        if self.disbursement_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.disbursement_request_ids.id
        else:
            action["domain"] = [("id", "in", self.disbursement_request_ids.ids)]
        action["context"] = {}
        return action
