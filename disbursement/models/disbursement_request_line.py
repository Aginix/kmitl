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

    # Not required: filled from the account when left blank.
    name = fields.Text(
        string="Description",
    )

    note = fields.Text(
        string="Note",
    )

    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
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
        required=True,
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
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

    # Only payees of the request's type are offered; a mismatch (e.g. the
    # header type changed afterwards) is caught by an exception rule on submit.
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="restrict",
        domain="[('partner_type_id', '=', parent.partner_type_id)]",
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

    @api.depends("amount", "tax_ids")
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
            partner=self.partner_id,
            currency=self.request_id.currency_id,
            taxes=self.tax_ids,
            price_unit=self.amount,
            quantity=1.0,
            account=self.account_id,
            analytic_distribution=self.analytic_distribution,
        )

    @api.onchange("account_id")
    def _onchange_account_id(self):
        if self.account_id:
            self.name = self.account_id.name

    # -------------------------------------------------------------------------
    # Partner compute methods
    # -------------------------------------------------------------------------
    # bank_ids too: a user who adds the missing account on the partner gets it
    # filled in here without re-picking the partner.
    @api.depends(
        "partner_id",
        "partner_id.bank_ids",
        "request_id.company_id",
        "request_id.pays_out",
    )
    def _compute_line_partner_bank_id(self):
        for line in self:
            # Only a line that can still be edited (a draft, or a station that
            # opens the lines) follows the partner's accounts: a submitted or
            # paid line keeps the account it was checked and paid against even
            # if the partner's accounts are archived or replaced later.
            request = line.request_id
            if request.state not in (False, "draft") and not request.can_edit_lines:
                line.partner_bank_id = line.partner_bank_id
            elif line.partner_id and request.pays_out:
                banks = line.partner_id.bank_ids.filtered(
                    lambda b: (
                        not b.company_id or b.company_id == line.request_id.company_id
                    )
                )
                # Keep a still-valid choice: a new account on the partner must
                # not re-point lines that already have one.
                current = line.partner_bank_id
                line.partner_bank_id = current if current in banks else banks[:1]
            else:
                line.partner_bank_id = False

    def _requires_partner_bank(self):
        """Whether this payee is paid into a bank account (hook: e.g. a
        cheque payee needs none). A request that pays no money out needs none."""
        self.ensure_one()
        return self.request_id.pays_out

    @api.constrains("partner_id")
    def _check_line_partner_required(self):
        for line in self:
            if not line.partner_id:
                raise ValidationError(_("Partner is required on each line."))

    # -------------------------------------------------------------------------
    # WHT methods
    # -------------------------------------------------------------------------
    @api.depends("partner_id.partner_type_id.wht_tax_id", "request_id.has_tax")
    def _compute_wht_tax_id(self):
        for line in self:
            line.wht_tax_id = (
                line.request_id.has_tax and line.partner_id.partner_type_id.wht_tax_id
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
