# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveRequest(models.Model):
    _name = "account.move.request"
    _description = "Account Move Request"
    _inherit = ["analytic.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "validated": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )

    ref = fields.Char(
        string="Reference",
        tracking=True,
        states=READONLY_STATES,
    )

    payment_type = fields.Selection(
        selection=[("direct", "Direct paid"), ("loan", "Loan"), ("prepaid", "Prepaid")],
        required=True,
        tracking=True,
        string="Payment Type",
        states=READONLY_STATES,
    )

    bill_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        readonly=True,
        copy=False,
        help="Link to the created vendor bill",
    )

    bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_bill_count",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        states=READONLY_STATES,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        states=READONLY_STATES,
    )

    line_ids = fields.One2many(
        comodel_name="account.move.request.line",
        inverse_name="request_id",
        string="Request Lines",
        copy=True,
        states=READONLY_STATES,
    )

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amount_all",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    amount_tax = fields.Monetary(
        string="Taxes",
        compute="_compute_amount_all",
        store=True,
        currency_field="currency_id",
    )

    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_all",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    tax_totals = fields.Json(
        compute="_compute_tax_totals",
        exportable=False,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("validated", "Validated"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    analytic_distribution = fields.Json(
        inverse="_inverse_analytic_distribution",
        copy=False,
    )

    @api.depends("bill_id")
    def _compute_bill_count(self):
        """Compute the number of bills linked to this request"""
        for record in self:
            record.bill_count = 1 if record.bill_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number"""
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.move.request"
                ) or "/"
        return super().create(vals_list)

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax", "line_ids.price_total")
    def _compute_amount_all(self):
        """Aggregate amounts from lines with tax calculation (mirrors PO logic)"""
        for request in self:
            request_lines = request.line_ids

            # Check company rounding method
            if (
                request.company_id.tax_calculation_rounding_method
                == "round_globally"
            ):
                # More accurate: compute all lines together
                tax_results = self.env["account.tax"]._compute_taxes(
                    [
                        line._convert_to_tax_base_line_dict()
                        for line in request_lines
                    ]
                )
                totals = tax_results["totals"].get(request.currency_id, {})
                amount_untaxed = totals.get("amount_untaxed", 0.0)
                amount_tax = totals.get("amount_tax", 0.0)
            else:
                # Faster: sum individual line amounts (round per line)
                amount_untaxed = sum(request_lines.mapped("price_subtotal"))
                amount_tax = sum(request_lines.mapped("price_tax"))

            request.amount_untaxed = amount_untaxed
            request.amount_tax = amount_tax
            request.amount_total = amount_untaxed + amount_tax

    @api.depends_context("lang")
    @api.depends(
        "line_ids.tax_ids",
        "line_ids.price_subtotal",
        "amount_total",
        "amount_untaxed",
    )
    def _compute_tax_totals(self):
        """Prepare detailed tax display information (mirrors PO logic)"""
        for request in self:
            request.tax_totals = self.env["account.tax"]._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in request.line_ids],
                request.currency_id,
            )

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all request lines"""
        if self.analytic_distribution:
            self.line_ids.update(
                {"analytic_distribution": self.analytic_distribution}
            )

    def _inverse_analytic_distribution(self):
        """When set analytic_distribution set analytic distribution on all request lines"""
        for request in self:
            if request.analytic_distribution:
                request.line_ids.write(
                    {"analytic_distribution": request.analytic_distribution})

    def _create_bill(self):
        """Create vendor bill from move request"""
        self.ensure_one()

        # Only allow creating bill from validated requests
        if self.state != "validated":
            raise UserError(_("Only validated requests can be used to create bills."))

        # Prepare invoice lines from request lines
        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append(
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "account_id": line.account_id.id,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "tax_ids": [Command.set(line.tax_ids.ids)],
                        "analytic_distribution": line.analytic_distribution,
                    }
                )
            )

        # Create vendor bill
        bill = self.env["account.move"].create(
            {
                "partner_id": self.partner_id.id,
                "move_type": "in_invoice",
                "invoice_date": self.date,
                "ref": self.ref,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "invoice_line_ids": invoice_lines,
            }
        )

        # Link the bill to this request
        self.bill_id = bill.id

        return bill

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            record.state = "submitted"
        return True

    def action_validate(self):
        """Validate the request"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be validated."))
            record.state = "validated"
        return True

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            if record.state == "cancel":
                raise UserError(_("Request is already cancelled."))
            record.state = "cancel"
        return True

    def action_view_bill(self):
        """Open the linked vendor bill"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "res_id": self.bill_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_bill(self):
        bill = self._create_bill()

        # Return action to open the created bill
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": bill.id,
            "view_mode": "form",
            "target": "current",
        }
