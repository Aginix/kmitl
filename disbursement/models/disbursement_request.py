# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Two-approver step on the DR: the Finance Division Director (ผอ.กองคลัง)
# approves first, then the Rector-delegated approver (ผู้ได้รับมอบอำนาจอธิการบดี).
# The budget is obligated/consumed only on the second (Rector) approval.
FINANCE_DIRECTOR_GROUP = "disbursement.group_disbursement_finance_director"
RECTOR_DELEGATE_GROUP = "disbursement.group_disbursement_rector_delegate"
# Execution Todos pushed to each approver group so the approval surfaces in the
# unified Todo notification center; cleared by acting on the DR, not "Mark read".
DR_APPROVE_FINANCE_ACTIVITY = "disbursement.mail_activity_dr_approve_finance"
DR_APPROVE_RECTOR_ACTIVITY = "disbursement.mail_activity_dr_approve_rector"
# Pushed to the requester when an approver rejects the request.
DR_REJECTED_ACTIVITY = "disbursement.mail_activity_dr_rejected"


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

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "signed": [("readonly", True)],
        "verified": [("readonly", True)],
        "approved": [("readonly", True)],
        "bills_posted": [("readonly", True)],
        # Post-bill payment-execution phase (disbursement_finance_kmitl):
        # the request is fully locked once it enters this phase.
        "payment_audited": [("readonly", True)],
        "payment_authorized": [("readonly", True)],
        "paid": [("readonly", True)],
        "cleared": [("readonly", True)],
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
        default="multi",
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

    payment_type = fields.Selection(
        selection=[
            ("direct", "Direct paid"),
            ("advance", "Advance"),
            ("prepaid", "Prepaid"),
        ],
        string="Payment Type",
        default="direct",
        tracking=True,
        states=READONLY_STATES,
    )

    note = fields.Text(
        string="Note",
        states=READONLY_STATES,
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

    wht_line_ids = fields.One2many(
        comodel_name="disbursement.request.line",
        inverse_name="request_id",
        string="WHT Lines",
        readonly=True,
        copy=False,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        domain=[("res_model", "=", "disbursement.request")],
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
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    pipeline_status = fields.Selection(
        selection=[
            ("pre_approval", "Pre-approval"),
            ("approved", "Approved"),
        ],
        string="Pipeline Status",
        compute="_compute_pipeline_status",
        store=True,
        readonly=True,
        copy=False,
        default="pre_approval",
    )

    display_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("signed", "Signed"),
            ("verified", "Verified"),
            ("approved", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        compute="_compute_display_status",
        store=True,
        readonly=True,
        copy=False,
        default="draft",
    )

    # Two-approver sub-workflow, tracked in parallel with ``state`` (which stays
    # ``verified`` for both approval steps). Kept separate so the accounting /
    # finance bridges and the return flow, which key off ``state``, are untouched.
    approval_state = fields.Selection(
        selection=[
            ("none", "None"),
            ("pending_finance", "Pending Finance Director"),
            ("pending_rector", "Pending Rector-delegated Approver"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval",
        default="none",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    finance_approver_id = fields.Many2one(
        "res.users", string="Finance Director", copy=False, readonly=True
    )
    finance_approve_date = fields.Datetime(
        string="Finance Approved On", copy=False, readonly=True
    )
    rector_approver_id = fields.Many2one(
        "res.users", string="Rector-delegated Approver", copy=False, readonly=True
    )
    rector_approve_date = fields.Datetime(
        string="Rector Approved On", copy=False, readonly=True
    )
    approval_reject_reason = fields.Text(
        string="Approval Reject Reason", copy=False, readonly=True
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

    budget_consumed_amount = fields.Monetary(
        string="Budget Consumed",
        currency_field="currency_id",
        copy=False,
        readonly=True,
        tracking=True,
    )

    budget_consumed_date = fields.Datetime(
        string="Budget Consumed At",
        copy=False,
        readonly=True,
    )

    # Leftover reserved budget still on the linked commitment (reserved −
    # obligated). Drives the "ส่งคืนเงินเหลือจ่าย" button visibility.
    budget_available_to_obligate = fields.Monetary(
        related="budget_commitment_id.available_to_obligate",
        string="งบจองคงเหลือ",
        currency_field="currency_id",
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
        store=True,
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

    @api.constrains("analytic_distribution", "state")
    def _check_analytic_distribution_complete(self):
        required_plan_codes = set(self._analytic_keys.keys())
        for rec in self:
            if rec.state in ("draft", "cancel"):
                continue
            if not rec.analytic_distribution:
                raise ValidationError(_("Analytic distribution is required."))
            account_ids = [int(k) for k in rec.analytic_distribution.keys()]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            present_codes = set(accounts.mapped("root_plan_id.code"))
            missing = required_plan_codes - present_codes
            if missing:
                raise ValidationError(
                    _("Missing required analytic dimensions: %s")
                    % ", ".join(sorted(missing))
                )

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

    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        # Reset every convenience field first so a stored one (here
        # department_analytic_id, used for the "Group By Department" filter)
        # does not keep a stale value when its dimension is removed from the
        # distribution. The shared mixin only assigns dimensions that are
        # present, so without this reset a stored field would never clear.
        for rec in self:
            for field_name in self._analytic_keys.values():
                rec[field_name] = False
        return super()._compute_analytic_id()

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
        self._compute_analytic()

    def _compute_analytic(self):
        """Hook for extension modules to merge analytics from reference document."""

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends("state")
    def _compute_pipeline_status(self):
        """Pipeline status reflects downstream document progress.

        Core only knows pre_approval / approved. Bridge modules
        (disbursement_accounting_kmitl, disbursement_finance_kmitl) extend
        the selection and override this compute to add bill_*/payment_*/done.
        """
        for rec in self:
            rec.pipeline_status = (
                "approved" if rec.state == "approved" else "pre_approval"
            )

    @api.depends("state", "pipeline_status")
    def _compute_display_status(self):
        """Unify state + pipeline_status into one user-visible value.

        Used by the form statusbar so the user sees a single progressive
        bar from draft → ... → approved → bill_* → payment_* → done. The
        two-approver sub-workflow is shown separately by its own
        ``approval_state`` status bar, not merged in here. The underlying
        state and pipeline_status fields still drive button visibility,
        security, and search filters.
        """
        for rec in self:
            if rec.state == "cancel":
                rec.display_status = "cancel"
            elif rec.state != "approved":
                rec.display_status = rec.state
            elif rec.pipeline_status in (False, "pre_approval", "approved"):
                rec.display_status = "approved"
            else:
                rec.display_status = rec.pipeline_status

    @api.depends("partner_id", "company_id")
    def _compute_partner_bank_id(self):
        for request in self:
            bank_ids = request.partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == request.company_id
            )
            request.partner_bank_id = bank_ids[0] if bank_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number and log budget commitment.

        The DR name follows the pattern DR/<fy>/<padding> (e.g. DR/69/0001),
        mirroring the per-fiscal-year scheme that purchase_request_sequence_kmitl
        uses. A dedicated ir.sequence is created on first use per fiscal year.
        """
        Sequence = self.env["ir.sequence"].sudo()
        Company = self.env["res.company"]
        for vals in vals_list:
            if vals.get("name") and vals["name"] != "/":
                continue

            date = fields.Date.to_date(
                vals.get("date") or fields.Date.context_today(self)
            )
            company = Company.browse(
                vals.get("company_id") or self.env.company.id
            )
            fy = company.find_daterange_fy(date) if company else False
            fy_year = fy.name[-2:] if fy else date.strftime("%y")

            seq_code = f"disbursement.request.{fy_year}"
            if not Sequence.search([("code", "=", seq_code)], limit=1):
                Sequence.create({
                    "name": f"Disbursement Request {fy_year}",
                    "code": seq_code,
                    "prefix": f"DR/{fy_year}/",
                    "padding": 4,
                    "number_increment": 1,
                })

            vals["name"] = Sequence.next_by_code(seq_code) or "/"

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

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            if not record.line_ids:
                raise UserError(
                    _("Cannot submit a disbursement request with no lines. "
                      "Please add at least one line.")
                )
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
        """Inspector validates the request and opens the two-approver step.

        The verified request now needs two approvals in sequence: the Finance
        Division Director (ผอ.กองคลัง) then the Rector-delegated approver
        (ผู้ได้รับมอบอำนาจอธิการบดี). Entering ``verified`` starts the sub-workflow
        at ``pending_finance`` and pushes a Todo to the Finance Director group.
        """
        for record in self:
            if record.state != "signed":
                raise UserError(_("Only signed requests can be validated."))
            record.state = "verified"
            record.approval_state = "pending_finance"
            record._schedule_approval_todo(
                FINANCE_DIRECTOR_GROUP, DR_APPROVE_FINANCE_ACTIVITY
            )
        return True

    def action_approve_finance(self):
        """First approval: the Finance Division Director (ผอ.กองคลัง).

        Records the sign-off and hands over to the Rector-delegated approver.
        No budget is touched yet — that happens only on the second approval.
        """
        for record in self:
            if record.state != "verified" or record.approval_state != "pending_finance":
                raise UserError(
                    _("Only a verified request awaiting the Finance Director "
                      "can be approved at this step.")
                )
            record.finance_approver_id = self.env.user
            record.finance_approve_date = fields.Datetime.now()
            record.activity_feedback([DR_APPROVE_FINANCE_ACTIVITY])
            record.approval_state = "pending_rector"
            record._schedule_approval_todo(
                RECTOR_DELEGATE_GROUP, DR_APPROVE_RECTOR_ACTIVITY
            )
        return True

    def action_approve(self):
        """Final approval: the Rector-delegated approver commits the budget.

        Only reachable once the Finance Director has approved
        (``approval_state == 'pending_rector'``). This is the single point where
        the budget is obligated and consumed.
        """
        for record in self:
            if record.state != "verified" or record.approval_state != "pending_rector":
                raise UserError(
                    _("Only a request awaiting the Rector-delegated approval "
                      "can be approved.")
                )
            record._action_approve_budget()
            record.state = "approved"
            record.approval_state = "approved"
            record.rector_approver_id = self.env.user
            record.rector_approve_date = fields.Datetime.now()
            record.activity_feedback([DR_APPROVE_RECTOR_ACTIVITY])
        return True

    def action_approve_batch(self):
        """Approve many requests at once from the approver queue.

        Each request is approved in its own savepoint so one that fails (e.g.
        insufficient budget on the Rector step) does not roll back the rest.
        Dispatches by ``approval_state`` so it serves both approver queues, and
        returns a summary notification.
        """
        approved = self.env["disbursement.request"]
        failures = []
        for record in self:
            try:
                with self.env.cr.savepoint():
                    if record.approval_state == "pending_finance":
                        record.action_approve_finance()
                    elif record.approval_state == "pending_rector":
                        record.action_approve()
                    else:
                        continue
                approved |= record
            except (UserError, ValidationError) as error:
                self.env.invalidate_all()
                failures.append(
                    (record.display_name, error.args and error.args[0] or _("error"))
                )
            except Exception as error:  # noqa: BLE001 - isolate per-record failures
                self.env.invalidate_all()
                failures.append((record.display_name, str(error)))

        message = _("%s request(s) approved.") % len(approved)
        if failures:
            message += "\n" + _("Could not approve:") + "\n"
            message += "\n".join(
                "• %s — %s" % (name, reason) for name, reason in failures
            )
        if failures and not approved:
            notification_type = "danger"
        elif failures:
            notification_type = "warning"
        else:
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Approval"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failures),
            },
        }

    def action_open_reject_wizard(self):
        """Open the wizard that captures the rejection reason (either approver)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Approval"),
            "res_model": "disbursement.reject.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_reject(self, reason):
        """Reject the pending approval and notify the requester.

        Keeps the request at ``verified`` (``state`` untouched) and marks the
        sub-workflow ``rejected``; a Todo goes back to the requester and the
        request can be re-sent for approval via ``action_request_approval``.
        """
        self.ensure_one()
        if self.approval_state not in ("pending_finance", "pending_rector"):
            raise UserError(
                _("Only a request awaiting approval can be rejected.")
            )
        self.activity_unlink(
            [DR_APPROVE_FINANCE_ACTIVITY, DR_APPROVE_RECTOR_ACTIVITY]
        )
        self.approval_state = "rejected"
        self.approval_reject_reason = reason
        if self.user_id:
            self.activity_schedule(
                DR_REJECTED_ACTIVITY,
                user_id=self.user_id.id,
                note=reason or "",
            )
        self.message_post(
            body=_(
                "<p><b>Approval rejected</b></p><p>Reason: <b>%s</b></p>"
            ) % (reason or _("no reason given")),
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def action_request_approval(self):
        """Re-send a rejected request for approval, restarting at the Finance
        Director step."""
        self.ensure_one()
        if self.approval_state != "rejected":
            raise UserError(
                _("Only a rejected request can be re-sent for approval.")
            )
        self.activity_feedback([DR_REJECTED_ACTIVITY])
        self.write({
            "finance_approver_id": False,
            "finance_approve_date": False,
            "rector_approver_id": False,
            "rector_approve_date": False,
            "approval_reject_reason": False,
            "approval_state": "pending_finance",
        })
        self._schedule_approval_todo(
            FINANCE_DIRECTOR_GROUP, DR_APPROVE_FINANCE_ACTIVITY
        )
        return True

    def _schedule_approval_todo(self, group_xmlid, act_type_xmlid):
        """Push an execution Todo to every member of ``group_xmlid`` so the
        pending approval surfaces in their Todo inbox (mirrors the
        accounting_kmitl_workflow fan-out)."""
        group = self.env.ref(group_xmlid)
        for record in self:
            for approver in group.users:
                record.activity_schedule(
                    act_type_xmlid,
                    user_id=approver.id,
                    note=record.name or "",
                )

    def _reset_approval(self):
        """Reset the two-approver sub-workflow and drop its pending Todos.

        Called when a request leaves the approval window (cancel / draft /
        return-to-verification) so the next time it reaches ``verified`` the
        cycle starts fresh."""
        to_reset = self.filtered(lambda r: r.approval_state != "none")
        if not to_reset:
            return
        to_reset.activity_unlink([
            DR_APPROVE_FINANCE_ACTIVITY,
            DR_APPROVE_RECTOR_ACTIVITY,
            DR_REJECTED_ACTIVITY,
        ])
        to_reset.write({
            "approval_state": "none",
            "finance_approver_id": False,
            "finance_approve_date": False,
            "rector_approver_id": False,
            "rector_approve_date": False,
            "approval_reject_reason": False,
        })

    def _action_approve_budget(self):
        """Obligate and consume from the pre-linked budget commitment.

        The BC is expected to be set from an upstream process (PR/PO/PA);
        this method does NOT create a new BC. It posts an obligate and a
        consume line for the DR amount, leaving the BC open for other DRs.
        """
        self.ensure_one()
        # Idempotent: a request returned to verification (approved -> signed)
        # keeps its obligation, so re-approving must not double-cut the budget.
        if self._has_own_budget_obligation():
            return
        commitment = self._check_commitment_obligable()
        first_reserve = self._get_commitment_reserve_line(commitment)
        self.env["budget.commitment.line"].create(
            self._prepare_budget_obligate_lines(commitment, first_reserve)
        )
        self.budget_consumed_amount = self.amount_total
        self.budget_consumed_date = fields.Datetime.now()
        self.message_post(
            body=_("Budget obligated and consumed: %(amount)s on commitment %(name)s")
            % {"amount": self.amount_total, "name": commitment.name},
            subtype_xmlid="mail.mt_note",
        )

    def action_return_leftover_budget(self):
        """Shortcut from the DR to the leftover-return (คืนจอง) confirmation.

        Opens the same ``budget.commitment.return.wizard`` the commitment uses,
        scoped to this DR's linked commitment, and stamps this DR as the source
        document on the posted return line. The wizard works on the whole
        commitment (which may be shared across งวด), returning its full
        unconsumed remainder — consistent with the manual, no-guard policy.
        """
        self.ensure_one()
        commitment = self.budget_commitment_id
        if not commitment:
            raise UserError(_("No budget commitment linked to this request."))
        return commitment._action_return_leftover_wizard(
            res_model="disbursement.request", res_id=self.id
        )

    def _check_commitment_obligable(self):
        """Validate the linked commitment can absorb this DR's amount."""
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(
                _("Budget commitment is required before approval. "
                  "Please link one from the upstream document.")
            )
        commitment = self.budget_commitment_id
        if commitment.state not in ("reserved", "partial"):
            raise UserError(
                _("Cannot obligate: commitment %(name)s is in state '%(state)s' "
                  "(must be 'reserved' or 'partial').")
                % {"name": commitment.name, "state": commitment.state}
            )
        if commitment.available_to_obligate < self.amount_total:
            raise UserError(
                _("Insufficient available to obligate on commitment %(name)s. "
                  "Available: %(available)s, Required: %(required)s")
                % {
                    "name": commitment.name,
                    "available": commitment.available_to_obligate,
                    "required": self.amount_total,
                }
            )
        return commitment

    def _get_commitment_reserve_line(self, commitment):
        """Return the first active reserve line on the commitment."""
        first_reserve = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )[:1]
        if not first_reserve:
            raise UserError(
                _("No active reserve line on commitment %s.") % commitment.name
            )
        return first_reserve

    def _prepare_budget_obligate_lines(self, commitment, reserve_line):
        """Build the obligate + consume commitment lines for this DR."""
        self.ensure_one()
        common = {
            "commitment_id": commitment.id,
            "account_id": reserve_line.account_id.id,
            "analytic_distribution": reserve_line.analytic_distribution,
            "amount": self.amount_total,
            "res_model": "disbursement.request",
            "res_id": self.id,
        }
        return [
            dict(common, move_type="obligate",
                 name=_("Obligation: %s") % self.name),
            dict(common, move_type="consume",
                 name=_("Consumption: %s") % self.name),
        ]

    def _reverse_own_commitment_lines(self, commitment):
        """Cancel only the obligate/consume lines THIS request created on a
        shared commitment, leaving the reservation open for other requests."""
        self.ensure_one()
        own = commitment.line_ids.filtered(
            lambda l: l.state == "posted"
            and l.move_type in ("obligate", "consume")
            and l.res_model == "disbursement.request"
            and l.res_id == self.id
        )
        own.action_cancel()
        return True

    def _is_pooled_commitment(self, commitment):
        """Whether the commitment belongs to an upstream document that pools it
        across many disbursement requests, so cancelling one request may only
        reverse its own lines and never the reservation itself.

        Core knows the procurement plan; bridge modules extend this for their own
        source documents (e.g. ``kmitl_project_disbursement`` for a project's
        shared reservation)."""
        self.ensure_one()
        return bool(
            "procurement_plan_id" in commitment._fields
            and commitment.procurement_plan_id
        )

    def _has_own_budget_obligation(self):
        """Whether this request already has a posted obligate line on its
        commitment (used to keep _action_approve_budget idempotent across a
        return-to-verification round trip)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        return bool(commitment) and bool(
            commitment.line_ids.filtered(
                lambda l: l.state == "posted"
                and l.move_type == "obligate"
                and l.res_model == "disbursement.request"
                and l.res_id == self.id
            )
        )

    def action_cancel(self):
        """Cancel the request.

        Bridge modules override this to add bill/payment-specific guards
        and cleanup (cancel draft bills, block on posted bills/payments).
        """
        for record in self:
            if record.state == "cancel":
                raise UserError(
                    _("Cannot cancel an already cancelled request.")
                )
            commitment = record.budget_commitment_id
            if commitment:
                try:
                    is_shared = (
                        record._is_pooled_commitment(commitment)
                        or len(commitment.disbursement_request_ids) > 1
                    )
                    if is_shared:
                        record._reverse_own_commitment_lines(commitment)
                        record.message_post(
                            body=_(
                                "Reversed this request's lines on shared "
                                "commitment %s."
                            )
                            % commitment.name,
                            subtype_xmlid="mail.mt_note",
                        )
                    else:
                        record._cancel_budget_commitment()
                        record.message_post(
                            body=_("Budget commitment %s cancelled.")
                            % commitment.name,
                            subtype_xmlid="mail.mt_note",
                        )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: %s") % str(e),
                        subtype_xmlid="mail.mt_note",
                    )
            record.state = "cancel"
        self._reset_approval()
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
        self._reset_approval()
        return True

    def _compute_access_url(self):
        """Compute the portal URL for the disbursement request."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/disbursement/{request.id}"

    def _get_report_base_filename(self):
        """Return the base filename for the report."""
        self.ensure_one()
        return f"Disbursement Request-{self.name}"

    @api.model
    def _get_masked_acc_number(self, acc_number):
        """Mask a bank account number, keeping the first 3 and last 4 digits."""
        acc = acc_number or ""
        digit_positions = [i for i, c in enumerate(acc) if c.isdigit()]
        if len(digit_positions) <= 7:
            return acc
        keep = set(digit_positions[:3]) | set(digit_positions[-4:])
        return "".join(
            c if (not c.isdigit() or i in keep) else "X"
            for i, c in enumerate(acc)
        )

    def open_preview(self):
        """Open preview in portal."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": self.get_portal_url(),
        }
