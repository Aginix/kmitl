# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.tools import is_html_empty
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

# Before it enters the circuit a request may still be reset to draft or
# cancelled by its requester, and its description edited. Inside the circuit
# (in progress) only the people at the station holding it may pull it out, and
# once the circuit is done only the finance officers may cancel it.
PRE_APPROVAL_STATES = ("draft", "submitted", "signed")

# What a request's settlement stage (ขั้นการชำระ) is worth, to tell a walk back
# (the money un-did a step) from progress.
_SETTLEMENT_RANK = {"none": 0, "billed": 1, "settled": 2, "booked": 3}

# The parts of the document a station may let its people edit (``can_edit_*``).
_EDIT_KINDS = ("header", "lines", "attachments", "dimensions", "budget")


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _description = "Disbursement Request"
    _inherit = [
        "analytic.mixin",
        "mail.thread",
        "mail.activity.mixin",
        "base.exception",
        # Thai signature date formatting on the printed signature block.
        "thai.date.mixin",
    ]
    _order = "main_exception_id asc, date desc, id desc"

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
    )

    # เลขที่หนังสือ: stamped by disbursement_sarabun when e-Saraban issues the
    # หนังสือ's number; typed from the memo on a direct claim
    # (disbursement_direct_claim).
    memo_number = fields.Char(
        string="Memo Number",
        tracking=True,
        copy=False,
        index=True,
    )

    # วันที่หน่วยงานลงนาม: stamped when the request turns ``signed`` (the head's
    # e-Saraban signature) unless already set — a direct claim types the date
    # of its external memo (disbursement_direct_claim).
    sign_date = fields.Date(
        string="Head Signed On",
        tracking=True,
        copy=False,
    )

    # มีภาษี: off clears VAT and WHT from every line and hides the tax columns.
    has_tax = fields.Boolean(
        string="Taxable",
        default=True,
        tracking=True,
    )

    # Still editable before the request enters the circuit (see the form).
    note = fields.Html(string="Description")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )

    line_ids = fields.One2many(
        comodel_name="disbursement.request.line",
        inverse_name="request_id",
        string="Request Lines",
        copy=True,
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

    # Progress around the circuit (วงจร). Where the request is inside it, and
    # who holds it, is the station's business (disbursement_wc); where the
    # money has got is ``settlement_stage``.
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("signed", "Signed"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
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

    # ขั้นการชำระ: how far the money has got, derived from the bills and the
    # vouchers that exist and never written by anyone, so it walks back by
    # itself when a bill is reset or a cheque bounces. The bridges that own the
    # bills (disbursement_accounting_kmitl) and the vouchers
    # (disbursement_finance_kmitl) each contribute their leg.
    settlement_stage = fields.Selection(
        selection=[
            ("none", "Not Billed"),
            ("billed", "Billed"),
            ("settled", "Settled"),
            ("booked", "Booked"),
        ],
        string="Settlement Stage",
        compute="_compute_settlement_stage",
        store=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )

    # UI-only locks (the one enforced lock is the payee banking guard of
    # disbursement_finance_kmitl): a part of the request is editable while the
    # station holding it allows that part and the money has not started.
    can_edit_header = fields.Boolean(compute="_compute_can_edit")
    can_edit_lines = fields.Boolean(compute="_compute_can_edit")
    can_edit_attachments = fields.Boolean(compute="_compute_can_edit")
    can_edit_dimensions = fields.Boolean(compute="_compute_can_edit")
    can_edit_budget = fields.Boolean(compute="_compute_can_edit")

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
        action = self.env.ref("disbursement.action_disbursement_exception_confirm")
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
                raise ValidationError(_("A request paid to a company must be taxable."))

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
    def _compute_settlement_stage(self):
        """Nothing is billed until a bridge says so: each of them overrides
        this compute and declares only the dependencies it adds. ``state`` is
        the dependency that makes Odoo compute the stage when a request is
        created: a stored compute with no dependency at all is never marked
        for computation, and would stay empty."""
        for rec in self:
            rec.settlement_stage = "none"

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_edit(self):
        """Whether the current user's screen lets the part be edited: the state
        or the station opens it (``_can_edit_open``) and nothing blocks it
        (``_can_edit_blocked``). Bridges extend those two, never this compute,
        and declare only the ``@api.depends`` they add."""
        for rec in self:
            for kind in _EDIT_KINDS:
                rec["can_edit_" + kind] = rec._can_edit_open(
                    kind
                ) and not rec._can_edit_blocked(kind)

    def _can_edit_open(self, kind):
        """The state (or, with stations, the station) lets ``kind`` be edited."""
        self.ensure_one()
        return self.state == "draft"

    def _can_edit_blocked(self, kind):
        """Something blocks ``kind`` whatever the state allows (a bill, a budget
        commitment …)."""
        self.ensure_one()
        return False

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
            company = Company.browse(vals.get("company_id") or self.env.company.id)
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
            Sequence.create(
                {
                    "name": f"Disbursement Request {fy_year}",
                    "code": seq_code,
                    "prefix": prefix,
                    "padding": 4,
                    "number_increment": 1,
                }
            )
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
            if request.company_id.tax_calculation_rounding_method == "round_globally":
                # More accurate: compute all lines together
                tax_results = self.env["account.tax"]._compute_taxes(
                    [line._convert_to_tax_base_line_dict() for line in request_lines]
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
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})

    def _inverse_analytic_distribution(self):
        """When set analytic_distribution set analytic distribution on all request lines"""
        for request in self:
            if request.analytic_distribution:
                request.line_ids.write(
                    {"analytic_distribution": request.analytic_distribution}
                )

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            if not record.line_ids:
                raise UserError(
                    _(
                        "Cannot submit a disbursement request with no lines. "
                        "Please add at least one line."
                    )
                )
            if record.detect_exceptions() and not record.ignore_exception:
                return record._popup_exceptions()
            record._assign_number()
            record.state = "submitted"
        return True

    def action_sign(self):
        """Head of department signs; the request enters the circuit
        (``_on_signed``)."""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be signed."))
            record.state = "signed"
            if not record.sign_date:
                record.sign_date = fields.Date.context_today(record)
            record._on_signed()
        return True

    # -------------------------------------------------------------------------
    # Acts and the circuit. The acts themselves (validate, approve, bill,
    # audit, authorize, consume the budget …) belong to the modules that
    # implement them: they declare themselves here and call the seams below.
    # -------------------------------------------------------------------------
    @api.model
    def _disbursement_acts(self):
        """The acts the capability modules contribute, as dicts ``{code, name
        (lazy), kind, group (xmlid), states, sequence, module}``. ``states`` are
        the states the act may be done in (default: signed, in progress).
        Extend with ``super()``."""
        return []

    @api.model
    def _disbursement_act(self, code):
        return next((act for act in self._disbursement_acts() if act["code"] == code), {})

    def _disbursement_act_states(self, code):
        return self._disbursement_act(code).get("states", ("signed", "in_progress"))

    def _disbursement_act_applicable(self, code):
        """Whether the act concerns this request at all (a request that draws no
        budget has nothing to consume)."""
        return True

    def _disbursement_act_offered(self, code):
        """Whether the current user may do the act on this request now: the state
        allows it and the user holds the act's role."""
        self.ensure_one()
        act = self._disbursement_act(code)
        return bool(
            act
            and self.state in self._disbursement_act_states(code)
            and self.env.user.has_group(act["group"])
        )

    def _disbursement_check_act(self, code):
        """Guard every act method with this first. The state check is integrity —
        an act is only done on a request in the circuit, whoever asks, su
        included — the role check is bypassed under su."""
        act = self._disbursement_act(code)
        for record in self:
            if record.state not in record._disbursement_act_states(code):
                raise UserError(
                    _("This act cannot be done on a request that is %s.")
                    % dict(record._fields["state"]._description_selection(self.env))[
                        record.state
                    ]
                )
            if not self.env.su and not self.env.user.has_group(act["group"]):
                raise AccessError(_("You do not hold the role this act requires."))

    def _disbursement_act_done(self, code):
        """Call at the end of an act: records it where the request is routed
        (disbursement_wc) and lets bridges react (disbursement_validation_assignment)."""

    def _on_signed(self):
        """The request has just been signed (or, with the context key
        ``disbursement_resubmit``, resubmitted after a correction): it enters the
        circuit. Nothing routes it without disbursement_wc."""

    def _disbursement_check_send_back(self):
        """Whether the current user may take a request in the circuit out of it
        (reset to draft, cancel, send back)."""
        if not self.env.su and not self.env.user.has_group(
            "disbursement.group_disbursement_officer"
        ):
            raise AccessError(
                _("Only a disbursement officer can take a request out of the circuit.")
            )

    def _settlement_snapshot(self):
        """{request id: settlement stage}, to compare around an operation that
        may walk the money back."""
        return {rec.id: rec.settlement_stage for rec in self}

    def _settlement_check(self, before):
        """After an operation that may walk the money back: call
        ``_on_settlement_walked_back`` for every request whose stage dropped."""
        self.flush_recordset(["settlement_stage"])
        for rec in self:
            previous = before.get(rec.id)
            if previous and _SETTLEMENT_RANK[rec.settlement_stage] < _SETTLEMENT_RANK[previous]:
                rec._on_settlement_walked_back(previous)

    def _on_settlement_walked_back(self, previous_stage):
        """The money went back a step (a bill reset, a voucher cancelled, a cheque
        bounced); ``previous_stage`` is where it was."""

    def _stamp_signature(self, step):
        """Freeze the acting user's rendered identity as the signature for ``step``.

        A re-stamp supersedes the previous row of the same step, so the block
        keeps one active row per step. Mirrors
        ``sarabun.routing.step._signature_snapshot_vals`` (ADR-0009):
        ชื่อ / ตำแหน่ง / ลายเซ็น are captured now so a later HR edit never rewrites an
        already-signed ใบขอเบิก. The source is read under ``sudo`` — capturing the
        official-record identity must not depend on the actor's hr.employee read
        grants — and the row itself is created under ``sudo`` because the
        signature model is read-only to every group.
        """
        self.ensure_one()
        self._archive_signatures([step])
        user = self.env.user
        employee = user.sudo().employee_id
        return (
            self.env["disbursement.request.signature"]
            .sudo()
            .create(
                {
                    "request_id": self.id,
                    "step": step,
                    "signed_by_id": user.id,
                    "signed_date": fields.Datetime.now(),
                    "signed_name": employee.name or user.name,
                    "signed_position_name": employee.job_title or "",
                    "signed_signature": employee.signature or False,
                }
            )
        )

    def _archive_signatures(self, steps):
        """Archive the signature rows for ``steps`` on these requests.

        Called wherever the workflow clears the matching who-did-it stamp, so a
        superseded round stops printing while its history survives (ADR-0002).
        """
        self.env["disbursement.request.signature"].sudo().search(
            [
                ("request_id", "in", self.ids),
                ("step", "in", steps),
            ]
        ).write({"active": False})

    # -------------------------------------------------------------------------
    # Workflow hooks (overridden by disbursement_budget)
    # -------------------------------------------------------------------------
    def _on_cancel(self):
        """Called per request by ``action_cancel``, before it turns ``cancel``."""
        self.ensure_one()

    def action_cancel(self):
        """Cancel the request.

        Before the circuit its requester may; inside it only the people holding
        it at their station may (``_disbursement_check_send_back``); once the
        circuit is done only a disbursement officer may. Bridge modules override
        this to add bill/payment-specific guards and cleanup (cancel draft
        bills, block on posted bills/payments).
        """
        officer = self.env.su or self.env.user.has_group(
            "disbursement.group_disbursement_officer"
        )
        for record in self:
            if record.state == "cancel":
                raise UserError(_("Cannot cancel an already cancelled request."))
            if record.state == "in_progress":
                record._disbursement_check_send_back()
            elif record.state not in PRE_APPROVAL_STATES and not officer:
                raise UserError(
                    _(
                        "Only a disbursement officer can cancel a request once it "
                        "has gone through the circuit."
                    )
                )
            record._on_cancel()
            record.state = "cancel"
        return True

    def action_draft(self):
        """Reset to draft. A request in the circuit leaves it (the stations are
        disbursement_wc's business); every active signature is archived, and the
        modules that stamp who acted (validate, approve) clear their stamp."""
        for record in self:
            if record.state not in ("submitted", "signed", "in_progress", "cancel"):
                raise UserError(
                    _(
                        "Only submitted, signed, in progress or cancelled requests "
                        "can be reset to draft."
                    )
                )
            if record.state == "in_progress":
                record._disbursement_check_send_back()
            if record.settlement_stage != "none":
                raise UserError(
                    _(
                        "The money of this request has started (a bill is "
                        "posted): it can no longer be reset or sent back."
                    )
                )
            record.state = "draft"
            # Signed again on the next round.
            if not record._keep_sign_date_on_draft():
                record.sign_date = False
            record.exception_ids = False
            record.main_exception_id = False
            record.ignore_exception = False
        self.signature_ids.sudo().write({"active": False})
        return True

    def _keep_sign_date_on_draft(self):
        """A request returned for correction keeps the head's signature: it is
        resubmitted straight to verification (``action_resubmit_verification``)."""
        self.ensure_one()
        return self.returned_for_edit

    def unlink(self):
        if self.filtered(lambda r: r.state != "cancel"):
            raise UserError(_("Only cancelled requests can be deleted."))
        # Its budget moves and bills refer to it: keep it for the audit trail.
        # The final approval's signature row survives a cancel (archived).
        if (
            self.env["disbursement.request.signature"]
            .sudo()
            .with_context(active_test=False)
            .search_count(
                [("request_id", "in", self.ids), ("step", "=", "rector_approve")]
            )
        ):
            raise UserError(
                _("A request that was approved cannot be deleted, even once cancelled.")
            )
        return super().unlink()

    def _has_description(self):
        """Whether รายละเอียด holds content: a cleared Html editor leaves
        ``<p><br></p>`` behind (for templates rendered without is_html_empty)."""
        self.ensure_one()
        return not is_html_empty(self.note)

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

    @api.model
    def _get_masked_acc_number(self, acc_number):
        """Mask a bank account number, keeping the first 3 and last 4 digits."""
        acc = acc_number or ""
        digit_positions = [i for i, c in enumerate(acc) if c.isdigit()]
        if len(digit_positions) <= 7:
            return acc
        keep = set(digit_positions[:3]) | set(digit_positions[-4:])
        return "".join(
            c if (not c.isdigit() or i in keep) else "X" for i, c in enumerate(acc)
        )
