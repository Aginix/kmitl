# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DisbursementRequestLine(models.Model):
    _name = "disbursement.request.line"
    _description = "Disbursement Request Line"
    _inherit = ["analytic.mixin", "base.exception.method"]
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        domain=["|", ("company_id", "=", False), ("company_id", "=", "company_id")],
    )

    name = fields.Text(
        string="Description",
        required=True,
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        digits="Product Unit of Measure",
    )

    price_unit = fields.Float(
        string="Unit Price",
        digits="Product Price",
    )

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )

    price_tax = fields.Monetary(
        string="Tax",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )

    price_total = fields.Monetary(
        string="Total",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )

    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        domain=[
            ("type_tax_use", "=", "purchase"),
        ],
    )

    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        domain=[
            ("company_id", "=", "company_id"),
            ("deprecated", "=", False),
        ],
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="request_id.company_id",
        store=True,
        index=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="request_id.currency_id",
        store=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        compute="_compute_line_partner_id",
        store=True,
        readonly=False,
    )

    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank",
        compute="_compute_line_partner_bank_id",
        store=True,
        readonly=False,
        domain="[('partner_id', '=', partner_id)]",
    )

    analytic_distribution = fields.Json(
        copy=False,
    )

    # WHT field
    wht_tax_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="WHT",
        compute="_compute_wht_tax_id",
        store=True,
        readonly=False,
        check_company=True,
    )

    # Exception field
    ignore_exception = fields.Boolean(
        related="request_id.ignore_exception",
        store=True,
        string="Ignore Exceptions",
    )

    amount_wht = fields.Monetary(
        string="WHT Amount",
        compute="_compute_amount_wht",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("price_subtotal", "wht_tax_id", "wht_tax_id.amount")
    def _compute_amount_wht(self):
        for line in self:
            if line.wht_tax_id and line.price_subtotal:
                line.amount_wht = line.currency_id.round(
                    line.price_subtotal * line.wht_tax_id.amount / 100
                )
            else:
                line.amount_wht = 0.0

    @api.depends("quantity", "price_unit", "tax_ids")
    def _compute_amount(self):
        """Compute line amounts with tax calculation (mirrors PO logic)"""
        for line in self:
            tax_results = self.env["account.tax"]._compute_taxes(
                [line._convert_to_tax_base_line_dict()]
            )
            totals = list(tax_results["totals"].values())[0]
            amount_untaxed = totals["amount_untaxed"]
            amount_tax = totals["amount_tax"]

            line.update(
                {
                    "price_subtotal": amount_untaxed,
                    "price_tax": amount_tax,
                    "price_total": amount_untaxed + amount_tax,
                }
            )

    def _convert_to_tax_base_line_dict(self):
        """Convert disbursement line to tax computation format (mirrors PO logic)"""
        self.ensure_one()
        return self.env["account.tax"]._convert_to_tax_base_line_dict(
            self,
            partner=self.partner_id or self.request_id.partner_id,
            currency=self.request_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit,
            quantity=self.quantity,
            account=self.account_id,
            analytic_distribution=self.analytic_distribution,
        )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Update description, price, account, and taxes when product changes"""
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.standard_price
            # Set account: first from product, then from product category
            account = (
                self.product_id.property_account_expense_id
                or self.product_id.categ_id.property_account_expense_categ_id
            )
            if account:
                self.account_id = account
            # Set taxes from product
            if self.product_id.supplier_taxes_id:
                self.tax_ids = self.product_id.supplier_taxes_id

    # -------------------------------------------------------------------------
    # Partner compute methods
    # -------------------------------------------------------------------------
    @api.depends("request_id.partner_type", "request_id.partner_id")
    def _compute_line_partner_id(self):
        for line in self:
            if line.request_id.partner_type == "single":
                line.partner_id = line.request_id.partner_id

    @api.depends(
        "partner_id",
        "request_id.partner_type",
        "request_id.partner_bank_id",
        "request_id.company_id",
    )
    def _compute_line_partner_bank_id(self):
        for line in self:
            if line.request_id.partner_type == "single":
                line.partner_bank_id = line.request_id.partner_bank_id
            elif line.partner_id:
                banks = line.partner_id.bank_ids.filtered(
                    lambda b: not b.company_id
                    or b.company_id == line.request_id.company_id
                )
                line.partner_bank_id = banks[0] if banks else False
            else:
                line.partner_bank_id = False

    @api.constrains("partner_id")
    def _check_line_partner_required(self):
        for line in self:
            if line.request_id.partner_type == "multi" and not line.partner_id:
                raise ValidationError(
                    _("Partner is required on each line in multi-partner mode.")
                )

    # -------------------------------------------------------------------------
    # WHT methods
    # -------------------------------------------------------------------------
    @api.depends(
        "partner_id.partner_type_id.wht_tax_id",
        "request_id.partner_id.partner_type_id.wht_tax_id",
    )
    def _compute_wht_tax_id(self):
        for line in self:
            partner = line.partner_id or line.request_id.partner_id
            line.wht_tax_id = (
                partner.partner_type_id.wht_tax_id if partner else False
            )

    # -------------------------------------------------------------------------
    # Exception methods
    # -------------------------------------------------------------------------
    def _get_main_records(self):
        return self.mapped("request_id")

    @api.model
    def _reverse_field(self):
        return "disbursement_request_ids"

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("request_id")
