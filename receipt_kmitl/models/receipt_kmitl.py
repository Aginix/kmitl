# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Root plan code → convenience field. The only place a dimension is named.
ANALYTIC_KEYS = {
    "departments": "department_analytic_id",
    "sources": "source_analytic_id",
    "funds": "fund_analytic_id",
    "activities": "activity_analytic_id",
    "kmitl_project": "kmitl_project_analytic_id",
    "procurement_plan": "procurement_plan_analytic_id",
}

# Fields readonly from submitted (remittance submission) onwards.
READONLY_STATES = {
    "submitted": [("readonly", True)],
    "approved": [("readonly", True)],
    "done": [("readonly", True)],
    "cancelled": [("readonly", True)],
}

# description / payment_method editable in draft → approved.
FLEX_READONLY_STATES = {
    "done": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class ReceiptKmitl(models.Model):
    _name = "kmitl.receipt"
    _description = "KMITL Cash Receipt"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order = "date desc, id desc"
    _analytic_keys = ANALYTIC_KEYS

    name = fields.Char(
        string="Receipt Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "To Submit"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Issuing Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        index=True,
        required=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    payment_type = fields.Selection(
        [
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("transfer", "Money Transfer"),
        ],
        required=True,
        default="cash",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )
    payment_method_id = fields.Many2one(
        "kmitl.payment.method",
        string="Payment Method",
        required=True,
        check_company=True,
        domain="['&', '|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids),"
        " ('payment_type', '=', payment_type)]",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )
    cheque_number = fields.Char(
        string="Cheque Number",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )
    cheque_date = fields.Date(
        string="Cheque Date",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )
    transfer_date = fields.Date(
        string="Transfer Date",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )

    # --- Analytic dimensions (header-level, synced to lines) ---
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
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        default=lambda self: self.env.ref(
            "account_analytic_kmitl.source_2", raise_if_not_found=False
        ),
        store=True,
        index=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
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
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="KMITL Project",
        compute="_compute_analytic_id",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Procurement Plan",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )

    # --- Customer ---
    is_walkin = fields.Boolean(
        string="Walk-in Customer",
        default=True,
        states=READONLY_STATES,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        default=lambda self: self._default_partner_id(),
        tracking=True,
        states=READONLY_STATES,
    )
    customer_name = fields.Char(
        string="Customer Name (snapshot)",
        tracking=True,
        states=READONLY_STATES,
    )
    customer_tax_id = fields.Char(
        string="Tax ID (snapshot)",
        states=READONLY_STATES,
    )
    customer_address = fields.Text(
        string="Customer Address (snapshot)",
        states=READONLY_STATES,
    )
    customer_branch_code = fields.Char(
        string="Branch Code (snapshot)",
        states=READONLY_STATES,
    )

    description = fields.Text(states=FLEX_READONLY_STATES)
    note = fields.Text()
    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachments",
        help="Supporting evidence, e.g. bank transfer slips.",
    )
    line_ids = fields.One2many(
        "kmitl.receipt.line",
        "receipt_id",
        string="Lines",
        copy=True,
        states=READONLY_STATES,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        states=READONLY_STATES,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        states=READONLY_STATES,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    remittance_id = fields.Many2one(
        "kmitl.receipt.remittance",
        string="Receipt Remittance",
        readonly=True,
        copy=False,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Issued By",
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # Defaults & computes
    # -------------------------------------------------------------------------
    @api.model
    def _default_partner_id(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "receipt_kmitl.walkin_partner_id"
        )
        if param:
            try:
                return int(param)
            except (TypeError, ValueError):
                return False
        walkin = self.env.ref(
            "receipt_kmitl.partner_walkin", raise_if_not_found=False
        )
        return walkin.id if walkin else False

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    @api.model
    def get_receipt_dashboard(self, domain=None):
        currency_id = self.env.company.currency_id.id
        dashboard = {
            "to_report": {
                "description": _("To Report"),
                "amount": 0.0,
                "currency": currency_id,
            },
            "under_validation": {
                "description": _("Under Validation"),
                "amount": 0.0,
                "currency": currency_id,
            },
            "reported": {
                "description": _("Reported"),
                "amount": 0.0,
                "currency": currency_id,
            },
        }
        base_domain = [("state", "in", ["draft", "submitted", "approved", "done"])]
        if domain:
            base_domain = expression.AND([base_domain, domain])
        groups = self.read_group(
            base_domain,
            ["amount_total"],
            ["state"],
            lazy=False,
        )
        state_map = {
            "draft": "to_report",
            "submitted": "under_validation",
            "approved": "under_validation",
            "done": "reported",
        }
        for g in groups:
            bucket = state_map.get(g["state"])
            if bucket:
                dashboard[bucket]["amount"] += g.get("amount_total") or 0.0
        return dashboard

    def action_create_report(self):
        receipts = self.filtered(
            lambda r: r.state == "draft"
            and not r.remittance_id
            and r.date <= fields.Date.context_today(r)
        )
        if not receipts:
            raise UserError(
                _("No receipts eligible for remittance.")
            )
        departments = receipts.mapped("department_analytic_id")
        if len(departments) > 1:
            raise UserError(
                _("Selected receipts belong to different departments. "
                  "Please select receipts from the same department.")
            )
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": departments.id,
                "receipt_ids": [(6, 0, receipts.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.receipt.remittance",
            "res_id": remittance.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    # -------------------------------------------------------------------------
    # Analytic dimension sync (header → lines)
    # -------------------------------------------------------------------------
    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        # Reset first: the shared mixin only assigns dimensions that are
        # present in the JSON, so a stored field (department/source) would
        # keep a stale value when its dimension is removed from the
        # distribution.
        for rec in self:
            for field_name in self._analytic_keys.values():
                rec[field_name] = False
        return super()._compute_analytic_id()

    # Also onchange handlers (not just inverses): on an unsaved record the
    # inverse only runs at write(). Each must stay single-field — looping
    # over all six codes here would reassign analytic_distribution after the
    # first, invalidating every dimension field (they share one compute) and
    # wiping out the very field the user just edited before it's read.
    @api.onchange("department_analytic_id")
    def _inverse_department_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("departments")

    @api.onchange("source_analytic_id")
    def _inverse_source_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("sources")

    @api.onchange("fund_analytic_id")
    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    @api.onchange("activity_analytic_id")
    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    @api.onchange("kmitl_project_analytic_id")
    def _inverse_kmitl_project_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("kmitl_project")

    @api.onchange("procurement_plan_analytic_id")
    def _inverse_procurement_plan_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("procurement_plan")

    def _sync_analytic_to_lines(self):
        for rec in self:
            if rec.line_ids:
                rec.line_ids.write(
                    {"analytic_distribution": rec.analytic_distribution}
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_analytic_to_lines()
        for rec in records:
            if rec.name in ("/", False):
                rec.name = rec._get_receipt_sequence().next_by_id()
        return records

    # A write touching any of these must re-push the header distribution onto
    # the lines: the dimension fields (their inverse rewrites the JSON), the
    # JSON itself, and line_ids (a newly added line starts with no
    # distribution).
    _SYNC_TRIGGERS = frozenset(ANALYTIC_KEYS.values()) | {
        "analytic_distribution",
        "line_ids",
    }

    def write(self, vals):
        res = super().write(vals)
        if self._SYNC_TRIGGERS & set(vals):
            self._sync_analytic_to_lines()
        if "remittance_id" in vals and not vals.get("remittance_id"):
            detached = self.filtered(lambda r: r.state in ("submitted", "approved"))
            if detached:
                detached.write({"state": "draft"})
                for rec in detached:
                    rec.message_post(
                        body=_("Removed from remittance; returned to the pending pool.")
                    )
        return res

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange("payment_type")
    def _onchange_payment_type(self):
        if self.payment_type != "cheque":
            self.cheque_number = False
            self.cheque_date = False
        if self.payment_type != "transfer":
            self.transfer_date = False
        self.payment_method_id = False

    @api.onchange("is_walkin")
    def _onchange_is_walkin(self):
        if self.is_walkin:
            walkin_id = self._default_partner_id()
            if walkin_id:
                self.partner_id = walkin_id
                self._sync_customer_snapshot()
            self.customer_tax_id = False
            self.customer_branch_code = False
            self.customer_address = False

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        self._sync_customer_snapshot()

    def _sync_customer_snapshot(self):
        for rec in self:
            if not rec.partner_id:
                continue
            partner = rec.partner_id
            rec.customer_name = partner.name or rec.customer_name
            rec.customer_tax_id = partner.vat or rec.customer_tax_id
            address_parts = [
                partner.street,
                partner.street2,
                partner.city,
                partner.state_id.name if partner.state_id else None,
                partner.zip,
            ]
            address = ", ".join([p for p in address_parts if p])
            if address:
                rec.customer_address = address
            if hasattr(partner, "branch") and partner.branch:
                rec.customer_branch_code = partner.branch

    # -------------------------------------------------------------------------
    # Sequence
    # -------------------------------------------------------------------------
    @staticmethod
    def _get_fiscal_year_be(date):
        budget_year_ce = date.year + (1 if date.month >= 10 else 0)
        return budget_year_ce + 543

    def _get_fy_be(self):
        self.ensure_one()
        return self._get_fiscal_year_be(self.date)

    def _get_receipt_sequence(self):
        fy_be = self._get_fy_be()
        seq_code = "kmitl.receipt.%s" % fy_be
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Receipt FY%s" % fy_be,
                    "code": seq_code,
                    "prefix": "RC/%s/" % fy_be,
                    "padding": 4,
                    "implementation": "no_gap",
                    "company_id": False,
                }
            )
        return seq

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("line_ids", "amount_total")
    def _check_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line."))
            for line in rec.line_ids:
                if not line.account_id:
                    raise ValidationError(
                        _("Line '%s' has no income account.") % (line.name or "")
                    )
            if rec.amount_total <= 0:
                raise ValidationError(
                    _("The receipt total must be greater than zero.")
                )

    @api.constrains("payment_type", "cheque_number", "cheque_date", "transfer_date")
    def _check_payment_type_fields(self):
        for rec in self:
            if rec.payment_type == "cheque" and not (
                rec.cheque_number and rec.cheque_date
            ):
                raise ValidationError(
                    _("Cheque number and cheque date are required for "
                      "cheque payments.")
                )
            if rec.payment_type == "transfer" and not rec.transfer_date:
                raise ValidationError(
                    _("Transfer date is required for transfer payments.")
                )

    @api.constrains("payment_type", "payment_method_id")
    def _check_payment_method_matches_type(self):
        """The domain on payment_method_id is UI-only — import, API writes,
        and writes that skip the onchange can still pair a method with the
        wrong type. That mismatch isn't cosmetic: the printed receipt ticks
        its box from payment_type, the journal entry debits
        payment_method_id.account_id, and the summary report filters by
        payment_type.
        """
        for rec in self:
            method = rec.payment_method_id
            if method and method.payment_type != rec.payment_type:
                raise ValidationError(
                    _("Payment method '%s' does not match the receipt's "
                      "payment type.") % method.name
                )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    # Kept as internal method — called by remittance, not exposed as button.
    def _action_post(self):
        for rec in self:
            move = rec._create_move()
            rec.move_id = move.id
            rec.state = "done"
        return True

    def _prepare_debit_line_vals(self):
        self.ensure_one()
        method = self.payment_method_id
        return {
            "name": _("Receipt %s") % self.name,
            "account_id": method.account_id.id,
            "debit": self.amount_total,
            "credit": 0.0,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
        }

    def _prepare_move_line_vals(self, line):
        self.ensure_one()
        return {
            "name": line.name or self.name,
            "account_id": line.account_id.id,
            "debit": 0.0,
            "credit": line.amount,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "analytic_distribution": line.analytic_distribution,
        }

    def _prepare_move_vals(self, line_vals):
        self.ensure_one()
        return {
            "ref": self.name,
            "date": self.date,
            "journal_id": self.payment_method_id.journal_id.id,
            "company_id": self.company_id.id,
            "line_ids": line_vals,
        }

    def _create_move(self):
        self.ensure_one()
        method = self.payment_method_id
        if not method.account_id:
            raise UserError(
                _("Payment method '%s' has no debit account.") % method.name
            )
        line_vals = [(0, 0, self._prepare_debit_line_vals())]
        for line in self.line_ids:
            line_vals.append((0, 0, self._prepare_move_line_vals(line)))
        move = self.env["account.move"].create(self._prepare_move_vals(line_vals))
        move.action_post()
        return move

    def action_cancel(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Only draft receipts can be cancelled. "
                      "Reset to draft first.")
                )
            remittance = rec.remittance_id
            if remittance:
                # to_submit was merged into draft, so a receipt pulled into a
                # still-draft remittance is itself still draft and passes the
                # check above. Cancelling it without detaching would leave it
                # stuck both ways: the remittance can't submit (every receipt
                # must be draft) and the receipt can't reset to draft
                # (action_draft blocks while remittance_id is set) — so
                # detach it as part of cancelling.
                rec.write({"remittance_id": False, "state": "cancelled"})
                rec.message_post(
                    body=_("Cancelled and removed from remittance %s.")
                    % remittance.display_name
                )
                remittance.message_post(
                    body=_("Receipt %s was cancelled and removed from this "
                           "remittance.") % rec.name
                )
            else:
                rec.state = "cancelled"
        return True

    def action_draft(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(
                    _("Only cancelled receipts can be reset to draft.")
                )
            if rec.remittance_id:
                raise UserError(
                    _("Receipt %s is in remittance %s; detach it or "
                      "reset the remittance first.")
                    % (rec.name, rec.remittance_id.display_name)
                )
            rec.state = "draft"
        return True

    def action_view_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def action_view_remittance(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.receipt.remittance",
            "res_id": self.remittance_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_print_original(self):
        self.ensure_one()
        self.message_post(body=_("Original receipt printed."))
        return self._action_print_via_browser(is_copy=False)

    def action_print_copy(self):
        self.ensure_one()
        self.message_post(body=_("Copy of receipt printed."))
        return self._action_print_via_browser(is_copy=True)

    def _action_print_via_browser(self, is_copy=False):
        self.ensure_one()
        html = self.env["ir.actions.report"].with_context(
            receipt_copy=is_copy,
        )._render_qweb_html(
            "receipt_kmitl.action_report_receipt_kmitl", self.ids
        )[0]
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        return {
            "type": "ir.actions.client",
            "tag": "receipt_kmitl_print",
            "params": {"html": html},
        }

    def unlink(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(
                    _("Only cancelled receipts can be deleted.")
                )
        return super().unlink()
