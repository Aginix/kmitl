# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _description = "Disbursement Request"
    _inherit = [
        "analytic.mixin",
        "mail.thread",
        "mail.activity.mixin",
        "portal.mixin",
        "budget.commitment.mixin",
        "base.exception",
    ]
    _order = "main_exception_id asc, date desc, id desc"

    _commitment_id_field = "budget_commitment_id"
    _commitment_account_id_field = "budget_account_id"

    PIPELINE_STATES = (
        "bill_draft",
        "bill_posted",
        "payment_draft",
        "payment_posted",
    )

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "signed": [("readonly", True)],
        "verified": [("readonly", True)],
        "approved": [("readonly", True)],
        "bill_draft": [("readonly", True)],
        "bill_posted": [("readonly", True)],
        "payment_draft": [("readonly", True)],
        "payment_posted": [("readonly", True)],
        "done": [("readonly", True)],
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

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
        states=READONLY_STATES,
    )

    reference = fields.Reference(
        selection=[],
        string="Reference Document",
        states=READONLY_STATES,
    )

    reference_model = fields.Char(
        string="Reference Model",
        compute="_compute_reference_fields",
        store=True,
    )
    reference_model_name = fields.Char(
        string="Reference Document Type",
        compute="_compute_reference_fields",
        store=True,
    )

    partner_type = fields.Selection(
        selection=[
            ("single", "Single Partner"),
            ("multi", "Multiple Partners"),
        ],
        string="Partner Type",
        default="single",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=False,
        compute="_compute_partner_id",
        store=True,
        readonly=False,
        tracking=True,
        states=READONLY_STATES,
    )

    is_company = fields.Boolean(
        related="partner_id.is_company",
        string="Is Company",
        readonly=True,
    )

    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank",
        compute="_compute_partner_bank_id",
        store=True,
        readonly=False,
        tracking=True,
        states=READONLY_STATES,
        check_company=True,
        domain="[('partner_id', '=', partner_id)]",
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

    bill_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="disbursement_request_id",
        string="Vendor Bills",
        readonly=True,
        copy=False,
    )

    bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_bill_count",
    )

    bill_draft_count = fields.Integer(
        string="Draft Bill Count",
        compute="_compute_bill_count",
    )

    # --- Pipeline: Payment tracking ---
    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        compute="_compute_payment_ids",
        string="Payments",
    )
    payment_count = fields.Integer(
        compute="_compute_payment_ids",
        string="Payment Count",
    )
    hide_register_payment_button = fields.Boolean(
        compute="_compute_hide_register_payment_button",
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
        comodel_name="disbursement.request.line",
        inverse_name="request_id",
        string="Request Lines",
        copy=True,
        states=READONLY_STATES,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        domain=[("res_model", "=", "disbursement.request")],
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

    amount_wht = fields.Monetary(
        string="Withholding Tax",
        compute="_compute_amount_all",
        store=True,
        currency_field="currency_id",
    )

    amount_net = fields.Monetary(
        string="Net Total",
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
            ("signed", "Signed"),
            ("verified", "Verified"),
            ("approved", "Approved"),
            ("bill_draft", "Bill Draft"),
            ("bill_posted", "Bill Posted"),
            ("payment_draft", "Payment Draft"),
            ("payment_posted", "Payment Posted"),
            ("done", "Done"),
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

    # Budget fields
    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        domain=[("state", "not in", ["draft", "done", "cancel"])],
        tracking=True,
        copy=False,
        states=READONLY_STATES,
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        tracking=True,
        copy=False,
        states=READONLY_STATES,
    )

    # Analytic dimension fields
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        search="_search_source_analytic_id",
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    # Fiscal year field
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )

    # -------------------------------------------------------------------------
    # Budget commitment methods
    # -------------------------------------------------------------------------
    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        for rec in self:
            if rec.budget_commitment_id:
                budget = rec.budget_commitment_id
                rec.budget_account_id = budget.account_id
                rec.analytic_distribution = budget.analytic_distribution

    @api.constrains("analytic_distribution")
    def _check_analytic_distribution_complete(self):
        required_plan_codes = {"activities", "departments", "funds", "sources"}
        # for rec in self:
        #     if rec.state == "cancel":
        #         continue
        #     if not rec.analytic_distribution:
        #         raise ValidationError(_("Analytic distribution is required."))
        #     account_ids = [int(k) for k in rec.analytic_distribution.keys()]
        #     accounts = self.env["account.analytic.account"].browse(account_ids)
        #     present_codes = set(accounts.mapped("root_plan_id.code"))
        #     missing = required_plan_codes - present_codes
        #     if missing:
        #         raise ValidationError(
        #             _("Missing required analytic dimensions: %s")
        #             % ", ".join(missing)
        #         )

    @api.model
    def _search_source_analytic_id(self, operator, value):
        account_ids = []
        if type(value) == int:
            account_ids.append(value)
        else:
            account_ids = (
                self.env["account.analytic.account"]
                .search(
                    [
                        ("root_plan_id.code", "=", "sources"),
                        "|",
                        ("name", "ilike", value),
                        ("complete_name", "ilike", value),
                    ]
                )
                .mapped("id")
            )

        query = f"""
            SELECT id
            FROM {self._table}
            WHERE analytic_distribution ?| array[%s]
        """
        return [
            (
                "id",
                "inselect",
                (query, [[str(account_id) for account_id in account_ids]]),
            )
        ]

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    def _log_budget_commitment_linked(self):
        self.ensure_one()
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_(
                'The disbursement request <a href="%(link)s" target="_blank">\'%(name)s\'</a> has been linked to this record.'
            )
            % {"name": self.name, "link": link},
            subtype_xmlid="mail.mt_comment",
        )

    def _log_budget_commitment_unlinked(self):
        self.ensure_one()
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_("The disbursement request '%(name)s' has been unlinked.")
            % {"name": self.name},
            subtype_xmlid="mail.mt_comment",
        )

    # -------------------------------------------------------------------------
    # Fiscal year methods
    # -------------------------------------------------------------------------
    @api.depends("date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.date)
            company = rec.company_id
            rec.account_fiscal_year_id = (
                company and company.find_daterange_fy(date) or False
            )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    # -------------------------------------------------------------------------
    # Exception methods
    # -------------------------------------------------------------------------
    @api.model
    def _reverse_field(self):
        return "disbursement_request_ids"

    def detect_exceptions(self):
        all_exceptions = super().detect_exceptions()
        lines = self.mapped("line_ids")
        all_exceptions += lines.detect_exceptions()
        return all_exceptions

    @api.constrains("ignore_exception", "line_ids", "state")
    def disbursement_request_check_exception(self):
        disbursement_request = self.filtered(lambda s: s.state == "submitted")
        if disbursement_request:
            disbursement_request._check_exception()

    @api.onchange("line_ids")
    def onchange_ignore_exception(self):
        if self.state == "submitted":
            self.ignore_exception = False

    @api.model
    def _get_popup_action(self):
        action = self.env.ref(
            "disbursement.action_disbursement_exception_confirm"
        )
        return action

    # -------------------------------------------------------------------------
    # Reference fields compute
    # -------------------------------------------------------------------------
    @api.depends("reference")
    def _compute_reference_fields(self):
        for rec in self:
            if rec.reference:
                rec.reference_model = rec.reference._name
                ir_model = self.env["ir.model"].sudo().search(
                    [("model", "=", rec.reference._name)], limit=1
                )
                rec.reference_model_name = ir_model.name if ir_model else rec.reference._name
            else:
                rec.reference_model = False
                rec.reference_model_name = False

    @api.depends("reference")
    def _compute_partner_id(self):
        for rec in self:
            if rec.reference and hasattr(rec.reference, "partner_id"):
                rec.partner_id = rec.reference.partner_id
                rec.partner_type = "single"
        self._compute_analytic()

    @api.constrains("partner_type", "partner_id")
    def _check_partner_required(self):
        for rec in self:
            if rec.partner_type == "single" and not rec.partner_id:
                raise ValidationError(
                    _("Partner is required in single-partner mode.")
                )

    @api.onchange("partner_type")
    def _onchange_partner_type(self):
        if self.partner_type == "single":
            line_partners = self.line_ids.mapped("partner_id")
            if len(line_partners) > 1:
                self.line_ids.update(
                    {"partner_id": False, "partner_bank_id": False}
                )
                return {
                    "warning": {
                        "title": _("Warning"),
                        "message": _(
                            "Partner fields on lines have been cleared."
                        ),
                    }
                }
        elif self.partner_type == "multi":
            self.partner_id = False
            self.partner_bank_id = False

    def _compute_analytic(self):
        """Hook for extension modules to merge analytics from reference document."""

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends("bill_ids", "bill_ids.state")
    def _compute_bill_count(self):
        """Compute the number of bills linked to this request"""
        for record in self:
            record.bill_count = len(record.bill_ids)
            record.bill_draft_count = len(
                record.bill_ids.filtered(lambda b: b.state == "draft")
            )

    @api.depends("bill_ids", "bill_ids.state", "bill_ids.payment_state")
    def _compute_payment_ids(self):
        Payment = self.env["account.payment"]
        for rec in self:
            payments = Payment
            for bill in rec.bill_ids:
                # Reconciled payments (posted & matched)
                payments |= bill._get_reconciled_payments()
                # Draft/submitted payments awaiting posting (KMITL flow)
                payments |= Payment.search([
                    ("to_reconcile_payment_line_ids.move_id", "=", bill.id),
                ])
            rec.payment_ids = payments
            rec.payment_count = len(payments)

    @api.depends("bill_ids", "bill_ids.state", "bill_ids.payment_state")
    def _compute_hide_register_payment_button(self):
        for rec in self:
            has_payable = any(
                b.state == "posted"
                and b.payment_state in ("not_paid", "partial")
                for b in rec.bill_ids
            )
            rec.hide_register_payment_button = not has_payable

    def _update_state_from_pipeline(self):
        """Recompute state based on bill/payment status for records in pipeline."""
        Payment = self.env["account.payment"]
        for rec in self:
            if rec.state not in rec.PIPELINE_STATES:
                continue
            bills = rec.bill_ids
            if not bills:
                continue
            # All bills fully paid → done
            if all(b.payment_state == "paid" for b in bills):
                rec.state = "done"
                rec.message_post(
                    body=_("All payments complete. Disbursement done."),
                    subtype_xmlid="mail.mt_note",
                )
                continue
            # Collect all payments across all bills
            all_payments = Payment
            for bill in bills:
                all_payments |= bill._get_reconciled_payments()
                all_payments |= Payment.search(
                    [("to_reconcile_payment_line_ids.move_id", "=", bill.id)]
                )
            if all_payments.filtered(lambda p: p.state == "posted"):
                rec.state = "payment_posted"
            elif all_payments:
                rec.state = "payment_draft"
            elif all(b.state == "posted" for b in bills):
                rec.state = "bill_posted"
            else:
                rec.state = "bill_draft"

    @api.depends("partner_id", "company_id")
    def _compute_partner_bank_id(self):
        for request in self:
            bank_ids = request.partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == request.company_id
            )
            request.partner_bank_id = bank_ids[0] if bank_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number and log budget commitment"""
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "disbursement.request"
                ) or "/"
        records = super().create(vals_list)
        for rec in records:
            if rec.budget_commitment_id:
                rec._log_budget_commitment_linked()
        return records

    def write(self, values):
        # Log unlinking if budget_commitment_id is being changed
        if "budget_commitment_id" in values:
            for rec in self:
                # Only log if there's currently a budget commitment and it's being changed
                if (
                    rec.budget_commitment_id
                    and values.get("budget_commitment_id") != rec.budget_commitment_id.id
                ):
                    rec._log_budget_commitment_unlinked()

        res = super().write(values)

        # Log linking if budget_commitment_id is set to a value
        if "budget_commitment_id" in values and values.get("budget_commitment_id"):
            for rec in self:
                rec._log_budget_commitment_linked()

        return res

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.price_tax",
        "line_ids.price_total",
        "line_ids.amount_wht",
    )
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

            amount_wht = sum(request_lines.mapped("amount_wht"))
            amount_total = amount_untaxed + amount_tax

            request.amount_untaxed = amount_untaxed
            request.amount_tax = amount_tax
            request.amount_total = amount_total
            request.amount_wht = amount_wht
            request.amount_net = amount_total - amount_wht

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
        """Create vendor bill(s) from disbursement request."""
        self.ensure_one()

        if self.state != "approved":
            raise UserError(
                _("Only approved requests can be used to create bills.")
            )

        if self.partner_type == "single":
            bills = self._create_single_bill()
        else:
            bills = self._create_multi_bills()

        self.state = "bill_draft"

        for bill in bills:
            bill_link = "/web#id=%d&model=account.move&view_type=form" % bill.id
            self.message_post(
                body=_(
                    'Vendor Bill <a href="%(link)s" target="_blank">'
                    "%(name)s</a> has been created."
                )
                % {"link": bill_link, "name": bill.name},
                subtype_xmlid="mail.mt_note",
            )

        return bills

    def _create_single_bill(self):
        """Create one bill for all lines (single-partner mode)."""
        self.ensure_one()
        invoice_lines = [
            Command.create(self._prepare_bill_line_vals(line))
            for line in self.line_ids
        ]
        bill = self.env["account.move"].create(
            self._prepare_bill_vals(
                self.partner_id, self.partner_bank_id, invoice_lines
            )
        )
        self._apply_wht_to_bill(bill, self.line_ids)
        return bill

    def _create_multi_bills(self):
        """Group lines by partner, create one bill per partner."""
        self.ensure_one()
        partner_lines = {}
        for line in self.line_ids:
            partner_lines.setdefault(
                line.partner_id,
                self.env["disbursement.request.line"],
            )
            partner_lines[line.partner_id] |= line

        bills = self.env["account.move"]
        for partner, lines in partner_lines.items():
            invoice_lines = [
                Command.create(self._prepare_bill_line_vals(line))
                for line in lines
            ]
            partner_bank = lines[0].partner_bank_id
            bill = self.env["account.move"].create(
                self._prepare_bill_vals(partner, partner_bank, invoice_lines)
            )
            self._apply_wht_to_bill(bill, lines)
            bills |= bill
        return bills

    def _prepare_bill_vals(self, partner, partner_bank, invoice_lines):
        """Prepare values for creating a vendor bill."""
        return {
            "disbursement_request_id": self.id,
            "partner_id": partner.id,
            "partner_bank_id": partner_bank.id if partner_bank else False,
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "ref": self.ref,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "invoice_line_ids": invoice_lines,
            "budget_commitment_id": self.budget_commitment_id.id,
            "budget_account_id": self.budget_account_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

    def _prepare_bill_line_vals(self, line):
        """Prepare values for a single invoice line."""
        return {
            "product_id": line.product_id.id,
            "name": line.name,
            "account_id": line.account_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "tax_ids": [Command.set(line.tax_ids.ids)],
            "analytic_distribution": line.analytic_distribution,
        }

    def _apply_wht_to_bill(self, bill, request_lines):
        """Apply WHT from request lines to the corresponding bill lines."""
        for request_line, invoice_line in zip(
            request_lines, bill.invoice_line_ids
        ):
            if request_line.wht_tax_id:
                invoice_line.wht_tax_id = request_line.wht_tax_id

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            if record.detect_exceptions() and not record.ignore_exception:
                return record._popup_exceptions()
            record.state = "submitted"
        return True

    def action_sign(self):
        """Head of department signs and sends to inspector"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be signed."))
            record.state = "signed"
        return True

    def action_validate(self):
        """Inspector validates the request"""
        for record in self:
            if record.state != "signed":
                raise UserError(_("Only signed requests can be validated."))
            record.state = "verified"
        return True

    def action_approve(self):
        """Director approves and commits budget"""
        for record in self:
            if record.state != "verified":
                raise UserError(
                    _("Only verified requests can be approved.")
                )
            record._action_approve_budget()
            record.state = "approved"
        return True

    def _action_approve_budget(self):
        """Reserve budget commitment on approval"""
        self.ensure_one()
        if self.budget_commitment_id:
            return
        if not self.budget_account_id:
            return
        check = self._check_budget_availability(
            amount=self.amount_total,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )
        if not check["is_sufficient"]:
            raise UserError(
                _(
                    "Insufficient budget. Available: %(available)s, "
                    "Required: %(required)s"
                )
                % {
                    "available": check["available"],
                    "required": self.amount_total,
                }
            )
        commitment = self._create_budget_commitment(
            amount=self.amount_total,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
            ref=self.name,
            description=_("Disbursement Request: %s") % self.name,
            auto_reserve=True,
        )
        self.message_post(
            body=_("Budget committed: %s") % commitment.name,
            subtype_xmlid="mail.mt_note",
        )

    def action_done(self):
        """Mark as done when bill is fully paid"""
        for record in self:
            if record.state not in record.PIPELINE_STATES:
                continue
            record.state = "done"
            record.message_post(
                body=_("Payment complete. Disbursement done."),
                subtype_xmlid="mail.mt_note",
            )
        return True

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            if record.state in ("cancel", "done"):
                raise UserError(
                    _("Cannot cancel a done or already cancelled request.")
                )
            posted_bills = record.bill_ids.filtered(
                lambda b: b.state == "posted"
            )
            if posted_bills:
                raise UserError(
                    _("Cannot cancel: bill(s) %s already posted. "
                      "Reverse the bill(s) first.")
                    % ", ".join(posted_bills.mapped("name"))
                )
            if record.bill_ids and record.payment_ids:
                raise UserError(
                    _("Cannot cancel: there are payments linked to bills. "
                      "Remove payments first.")
                )
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %s cancelled.")
                        % record.budget_commitment_id.name,
                        subtype_xmlid="mail.mt_note",
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: %s") % str(e),
                        subtype_xmlid="mail.mt_note",
                    )
            draft_bills = record.bill_ids.filtered(
                lambda b: b.state == "draft"
            )
            if draft_bills:
                draft_bills.button_cancel()
            record.state = "cancel"
        return True

    def action_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ("submitted", "signed", "cancel"):
                raise UserError(
                    _("Only submitted, sent, or cancelled requests can be reset to draft.")
                )
            record.state = "draft"
            record.exception_ids = False
            record.main_exception_id = False
            record.ignore_exception = False
        return True

    def action_view_bill(self):
        """Open the linked vendor bill(s)"""
        self.ensure_one()
        bills = self.bill_ids
        if len(bills) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Vendor Bill"),
                "res_model": "account.move",
                "res_id": bills.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "domain": [("id", "in", bills.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_register_payment(self):
        """Open payment wizard for unpaid posted bills."""
        self.ensure_one()
        unpaid_bills = self.bill_ids.filtered(
            lambda b: b.state == "posted"
            and b.payment_state in ("not_paid", "partial")
        )
        if not unpaid_bills:
            raise UserError(
                _("No posted unpaid bills to pay.")
            )
        return {
            "name": _("Register Payment"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "context": {
                "active_model": "account.move",
                "active_ids": unpaid_bills.ids,
                "dont_redirect_to_payments": True,
            },
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def action_view_payments(self):
        """Open related payment(s)."""
        self.ensure_one()
        if self.payment_count == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Payment"),
                "res_model": "account.payment",
                "res_id": self.payment_ids.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", self.payment_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_create_bill(self):
        bills = self._create_bill()

        if len(bills) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": bills.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "domain": [("id", "in", bills.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def _compute_access_url(self):
        """Compute the portal URL for the disbursement request."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/disbursement/{request.id}"

    def _get_report_base_filename(self):
        """Return the base filename for the report."""
        self.ensure_one()
        return f"Disbursement Request-{self.name}"

    def open_preview(self):
        """Open preview in portal."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": self.get_portal_url(),
        }
