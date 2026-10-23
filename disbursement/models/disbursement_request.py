# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Two-approver step on the DR: the Finance Division Director (ผอ.กองคลัง)
# approves first, then the Rector-delegated approver (ผู้ได้รับมอบอำนาจอธิการบดี).
# The final (Rector) approval is the hook disbursement_budget consumes on.
FINANCE_DIRECTOR_GROUP = "disbursement.group_disbursement_finance_director"
RECTOR_DELEGATE_GROUP = "disbursement.group_disbursement_rector_delegate"
# Execution Todos pushed to each approver group so the approval surfaces in the
# unified Todo notification center; cleared by acting on the DR, not "Mark read".
DR_APPROVE_FINANCE_ACTIVITY = "disbursement.mail_activity_dr_approve_finance"
DR_APPROVE_RECTOR_ACTIVITY = "disbursement.mail_activity_dr_approve_rector"
# Pushed to the requester when an approver rejects the request.
DR_REJECTED_ACTIVITY = "disbursement.mail_activity_dr_rejected"
# Up to the final approval a request may still be reset to draft or cancelled
# by its requester, and its description edited; past it only the finance
# officers may cancel it.
PRE_APPROVAL_STATES = ("draft", "submitted", "signed", "verified")


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _description = "Disbursement Request"
    _inherit = [
        "analytic.mixin",
        "mail.thread",
        "mail.activity.mixin",
        "portal.mixin",
        "base.exception",
        # Thai signature date formatting on the printed signature block.
        "thai.date.mixin",
    ]
    _order = "main_exception_id asc, date desc, id desc"

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

    # Every payee on the lines must be of this type (ประเภทผู้รับเงิน); the
    # payees themselves live on the lines only.
    partner_type_id = fields.Many2one(
        comodel_name="res.partner.type",
        string="Payee Type",
        required=True,
        tracking=True,
        index=True,
        ondelete="restrict",
        states=READONLY_STATES,
    )

    # Loaded on the form so มีภาษี can be locked for a company payee type.
    partner_type_company_type = fields.Selection(
        related="partner_type_id.company_type",
        string="Payee Company Type",
    )

    payee_display = fields.Char(
        string="Payees",
        compute="_compute_payee_display",
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
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

    # เลขที่หนังสือ: stamped by disbursement_sarabun when e-Saraban issues the
    # หนังสือ's number; typed from the memo on a direct claim
    # (disbursement_direct_claim).
    memo_number = fields.Char(
        string="Memo Number",
        tracking=True,
        copy=False,
        index=True,
        states=READONLY_STATES,
    )

    # วันที่หน่วยงานลงนาม: stamped when the request turns ``signed`` (the head's
    # e-Saraban signature) unless already set — a direct claim types the date
    # of its external memo (disbursement_direct_claim).
    sign_date = fields.Date(
        string="Head Signed On",
        tracking=True,
        copy=False,
        states=READONLY_STATES,
    )

    # มีภาษี: off clears VAT and WHT from every line and hides the tax columns.
    has_tax = fields.Boolean(
        string="Taxable",
        default=True,
        tracking=True,
        states=READONLY_STATES,
    )

    # Still editable until the request is approved.
    note = fields.Html(
        string="Description",
        states={
            state: modifier
            for state, modifier in READONLY_STATES.items()
            if state not in PRE_APPROVAL_STATES
        },
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
        index=True,
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
        index=True,
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
        index=True,
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
        index=True,
    )

    # Who actually pressed Validate. Distinct from ``assigned_to``
    # (disbursement_assignment_kmitl), which records who was *assigned* the
    # verification and may be a different person once takeover is allowed.
    verifier_id = fields.Many2one(
        "res.users", string="Verified By", copy=False, readonly=True
    )
    verify_date = fields.Datetime(
        string="Verified On", copy=False, readonly=True
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

    # Frozen signature snapshots, one per workflow step taken — the source of the
    # signature block on the printed ใบขอเบิก (ADR-0002).
    signature_ids = fields.One2many(
        "disbursement.request.signature",
        "request_id",
        string="Signatures",
        readonly=True,
    )

    analytic_distribution = fields.Json(
        inverse="_inverse_analytic_distribution",
        copy=False,
    )

    # Analytic dimension fields
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        compute_sudo=True,
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
        compute_sudo=True,
        tracking=True,
        index=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )

    # Stored, like department_analytic_id: the finance office groups its lists by
    # แหล่งเงิน, and read_group only accepts a database-persisted column.
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=True,
        compute_sudo=True,
        tracking=True,
        index=True,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    # Chosen freely (a stand-alone request may book to any year); defaults to
    # the year of ``date`` and drives the DR/<yy>/ number.
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        index=True,
        states=READONLY_STATES,
    )

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

    # Also onchange handlers (as in receipt_kmitl): the form sends the hidden
    # analytic_distribution with the dimensions on save, so it must already
    # hold them — else its stale value wins over these inverses and the
    # dimensions typed by hand are lost. One field per handler: reassigning
    # the distribution recomputes every dimension field.
    @api.onchange("activity_analytic_id")
    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    @api.onchange("department_analytic_id")
    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    @api.onchange("fund_analytic_id")
    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    @api.onchange("source_analytic_id")
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

    # -------------------------------------------------------------------------
    # Fiscal year methods
    # -------------------------------------------------------------------------
    @api.model
    def _default_fiscal_year(self, date, company):
        return company.find_daterange_fy(date) if company else False

    @api.onchange("date", "company_id")
    def _onchange_date_fiscal_year(self):
        """Default the year from the date. The year leads once set (it drives
        the number and, under budget control, the commitment), so a later
        date edit never moves it."""
        for rec in self.filtered(lambda r: not r.account_fiscal_year_id):
            rec.account_fiscal_year_id = rec._default_fiscal_year(
                fields.Date.to_date(rec.date), rec.company_id
            )

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
    # Payees and source document
    # -------------------------------------------------------------------------
    @api.depends("line_ids.partner_id")
    def _compute_payee_display(self):
        """First payee, plus how many others: "A +2"."""
        for rec in self:
            partners = rec.line_ids.partner_id
            rec.payee_display = partners[:1].display_name or ""
            if len(partners) > 1:
                rec.payee_display += " +%d" % (len(partners) - 1)

    @api.onchange("partner_type_id")
    def _onchange_partner_type_id(self):
        mismatched = self.line_ids.partner_id.filtered(
            lambda p: p.partner_type_id != self.partner_type_id
        )
        if self.partner_type_id and mismatched:
            return {
                "warning": {
                    "title": _("Payee type changed"),
                    "message": _(
                        "These payees are not of type %(type)s and must be "
                        "changed before submitting: %(names)s"
                    )
                    % {
                        "type": self.partner_type_id.display_name,
                        "names": ", ".join(mismatched.mapped("display_name")),
                    },
                }
            }

    # -------------------------------------------------------------------------
    # Taxable (มีภาษี)
    # -------------------------------------------------------------------------
    @api.onchange("payment_type", "partner_type_id")
    def _onchange_has_tax_default(self):
        """A company is always taxed; an advance or a prepayment starts out
        untaxed (the user may tick it back)."""
        if self.partner_type_id.company_type == "company":
            self.has_tax = True
        elif self.payment_type in ("advance", "prepaid"):
            self.has_tax = False

    @api.constrains("has_tax", "partner_type_id")
    def _check_has_tax_company(self):
        for rec in self:
            if not rec.has_tax and rec.partner_type_id.company_type == "company":
                raise ValidationError(
                    _("A request paid to a company must be taxable.")
                )

    @api.onchange("has_tax")
    def _onchange_has_tax(self):
        if not self.has_tax:
            self.line_ids.update({"tax_ids": [(5, 0, 0)], "wht_tax_id": False})

    def _clear_untaxed_lines(self):
        """Keep programmatic creates/writes consistent with ``has_tax``."""
        lines = self.filtered(lambda r: not r.has_tax).line_ids.filtered(
            lambda l: l.tax_ids or l.wht_tax_id
        )
        if lines:
            lines.write({"tax_ids": [(5, 0, 0)], "wht_tax_id": False})

    @api.model
    def _get_payee_type(self, partner):
        """The type a request paying ``partner`` must carry — for bridges that
        raise a request from a single-vendor document."""
        if not partner.partner_type_id:
            raise UserError(
                _("Set a payee type on %s before raising a disbursement request.")
                % partner.display_name
            )
        return partner.partner_type_id

    def _get_source_document(self):
        """The document this request was raised from (PO, PA, AR …), or an
        empty value for a stand-alone request. Each source bridge overrides it;
        it feeds the bill reference and the printed อ้างอิง line."""
        self.ensure_one()
        return False

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

    @api.model_create_multi
    def create(self, vals_list):
        """Default the fiscal year. The number is not drawn here but on submit
        (``_assign_number``): a draft stays "/" so abandoned drafts leave no
        gaps in the DR/<fy>/ sequence."""
        Company = self.env["res.company"]
        for vals in vals_list:
            date = fields.Date.to_date(
                vals.get("date") or fields.Date.context_today(self)
            )
            company = Company.browse(
                vals.get("company_id") or self.env.company.id
            )
            if not vals.get("account_fiscal_year_id"):
                fy = self._default_fiscal_year(date, company)
                vals["account_fiscal_year_id"] = fy.id if fy else False

        records = super().create(vals_list)
        records._clear_untaxed_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "has_tax" in vals or "line_ids" in vals:
            self._clear_untaxed_lines()
        if vals.get("account_fiscal_year_id"):
            # The number follows the year: a draft moved to another year gets
            # that year's next number.
            for rec in self.filtered(lambda r: r.state == "draft"):
                prefix = rec._number_prefix(rec.account_fiscal_year_id, rec.date)
                if rec.name.startswith("DR/") and not rec.name.startswith(prefix):
                    rec.name = rec._next_number(rec.account_fiscal_year_id, rec.date)
        return res

    def _assign_number(self):
        """Draw the DR/<fy>/<nnnn> number on first submit, mirroring the
        per-fiscal-year scheme of purchase_request_sequence_kmitl. A request
        reset to draft keeps its number."""
        for rec in self.filtered(lambda r: not r.name or r.name == "/"):
            rec.name = rec._next_number(rec.account_fiscal_year_id, rec.date)

    @api.model
    def _number_prefix(self, fiscal_year, date):
        """DR/<yy>/ of the chosen fiscal year (the date's year without one)."""
        fy_year = fiscal_year.name[-2:] if fiscal_year else date.strftime("%y")
        return f"DR/{fy_year}/"

    @api.model
    def _next_number(self, fiscal_year, date):
        """Next DR/<yy>/<nnnn>, from a per-year ir.sequence created on first use."""
        Sequence = self.env["ir.sequence"].sudo()
        prefix = self._number_prefix(fiscal_year, date)
        fy_year = prefix.split("/")[1]
        seq_code = f"disbursement.request.{fy_year}"
        if not Sequence.search([("code", "=", seq_code)], limit=1):
            Sequence.create({
                "name": f"Disbursement Request {fy_year}",
                "code": seq_code,
                "prefix": prefix,
                "padding": 4,
                "number_increment": 1,
            })
        return Sequence.next_by_code(seq_code) or "/"

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
            record._assign_number()
            record.state = "submitted"
        return True

    def action_sign(self):
        """Head of department signs and sends to inspector"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be signed."))
            record.state = "signed"
            if not record.sign_date:
                record.sign_date = fields.Date.context_today(record)
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
            record.verifier_id = self.env.user
            record.verify_date = fields.Datetime.now()
            record._stamp_signature("verify")
            record.approval_state = "pending_finance"
            record._schedule_approval_todo(
                FINANCE_DIRECTOR_GROUP, DR_APPROVE_FINANCE_ACTIVITY
            )
        return True

    def action_approve_finance(self):
        """First approval: the Finance Division Director (ผอ.กองคลัง).

        Records the sign-off and hands over to the Rector-delegated approver.
        Nothing downstream fires yet — that happens only on the second approval.
        """
        for record in self:
            if record.state != "verified" or record.approval_state != "pending_finance":
                raise UserError(
                    _("Only a verified request awaiting the Finance Director "
                      "can be approved at this step.")
                )
            record.finance_approver_id = self.env.user
            record.finance_approve_date = fields.Datetime.now()
            record._stamp_signature("finance_approve")
            record.activity_feedback([DR_APPROVE_FINANCE_ACTIVITY])
            record.approval_state = "pending_rector"
            record._schedule_approval_todo(
                RECTOR_DELEGATE_GROUP, DR_APPROVE_RECTOR_ACTIVITY
            )
        return True

    def action_approve(self):
        """Final approval by the Rector-delegated approver.

        Only reachable once the Finance Director has approved
        (``approval_state == 'pending_rector'``). This is the single point that
        fires ``_on_final_approval`` — where disbursement_budget consumes the
        budget.
        """
        for record in self:
            if record.state != "verified" or record.approval_state != "pending_rector":
                raise UserError(
                    _("Only a request awaiting the Rector-delegated approval "
                      "can be approved.")
                )
            record._on_final_approval()
            record.state = "approved"
            record.approval_state = "approved"
            record.rector_approver_id = self.env.user
            record.rector_approve_date = fields.Datetime.now()
            record._stamp_signature("rector_approve")
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
        self._archive_signatures(["finance_approve", "rector_approve"])
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

    def _stamp_signature(self, step):
        """Freeze the acting user's rendered identity as the signature for ``step``.

        Mirrors ``sarabun.routing.step._signature_snapshot_vals`` (ADR-0009):
        ชื่อ / ตำแหน่ง / ลายเซ็น are captured now so a later HR edit never rewrites an
        already-signed ใบขอเบิก. The source is read under ``sudo`` — capturing the
        official-record identity must not depend on the actor's hr.employee read
        grants — and the row itself is created under ``sudo`` because the
        signature model is read-only to every group.
        """
        self.ensure_one()
        user = self.env.user
        employee = user.sudo().employee_id
        return self.env["disbursement.request.signature"].sudo().create({
            "request_id": self.id,
            "step": step,
            "signed_by_id": user.id,
            "signed_date": fields.Datetime.now(),
            "signed_name": employee.name or user.name,
            "signed_position_name": employee.job_title or "",
            "signed_signature": employee.signature or False,
        })

    def _archive_signatures(self, steps):
        """Archive the signature rows for ``steps`` on these requests.

        Called wherever the workflow clears the matching who-did-it stamp, so a
        superseded round stops printing while its history survives (ADR-0002).
        """
        self.env["disbursement.request.signature"].sudo().search([
            ("request_id", "in", self.ids),
            ("step", "in", steps),
        ]).write({"active": False})

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

    def _reset_verification(self):
        """Drop the Validate stamp and archive its signature.

        Called wherever the request falls back to a state at or before ``signed``,
        from which the officer must verify again.
        """
        to_reset = self.filtered("verifier_id")
        if not to_reset:
            return
        to_reset._archive_signatures(["verify"])
        to_reset.write({"verifier_id": False, "verify_date": False})

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
        to_reset._archive_signatures(["finance_approve", "rector_approve"])
        to_reset.write({
            "approval_state": "none",
            "finance_approver_id": False,
            "finance_approve_date": False,
            "rector_approver_id": False,
            "rector_approve_date": False,
            "approval_reject_reason": False,
        })

    # -------------------------------------------------------------------------
    # Workflow hooks (overridden by disbursement_budget)
    # -------------------------------------------------------------------------
    def _on_final_approval(self):
        """Called by the Rector-delegated approval, before the request turns
        ``approved``; raising here aborts the approval."""
        self.ensure_one()

    def _on_cancel(self):
        """Called per request by ``action_cancel``, before it turns ``cancel``."""
        self.ensure_one()

    def action_cancel(self):
        """Cancel the request.

        Bridge modules override this to add bill/payment-specific guards
        and cleanup (cancel draft bills, block on posted bills/payments).
        """
        officer = self.env.su or self.env.user.has_group(
            "disbursement.group_disbursement_officer"
        )
        for record in self:
            if record.state == "cancel":
                raise UserError(
                    _("Cannot cancel an already cancelled request.")
                )
            if record.state not in PRE_APPROVAL_STATES and not officer:
                raise UserError(
                    _("Only a disbursement officer can cancel an approved request.")
                )
            record._on_cancel()
            record.state = "cancel"
        self._reset_approval()
        return True

    def action_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ("submitted", "signed", "verified", "cancel"):
                raise UserError(
                    _("Only submitted, signed, verified, or cancelled requests can be reset to draft.")
                )
            record.state = "draft"
            # Signed again on the next round.
            if not record._keep_sign_date_on_draft():
                record.sign_date = False
            record.exception_ids = False
            record.main_exception_id = False
            record.ignore_exception = False
        self._reset_verification()
        self._reset_approval()
        return True

    def _keep_sign_date_on_draft(self):
        """A request returned for correction keeps the head's signature: it is
        resubmitted straight to verification (``action_resubmit_verification``)."""
        self.ensure_one()
        return self.returned_for_edit

    def unlink(self):
        if self.filtered(lambda r: r.state != "cancel"):
            raise UserError(_("Only cancelled requests can be deleted."))
        return super().unlink()

    def name_get(self):
        # A draft has no number until its first submit (``_assign_number``).
        # A plain loop: _() finds the language from this frame's ``self``.
        result = []
        for rec in self:
            name = rec.name
            if not name or name == "/":
                name = _("Draft Request #%s") % (rec._origin.id or "")
            result.append((rec.id, name))
        return result

    def _compute_access_url(self):
        """Compute the portal URL for the disbursement request."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/disbursement/{request.id}"

    def _get_report_base_filename(self):
        """Return the base filename for the report."""
        self.ensure_one()
        return f"Disbursement Request-{self.display_name}"

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
