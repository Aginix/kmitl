# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

ANALYTIC_DIMENSION_FIELDS = [
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
    "activity_analytic_id",
    "kmitl_project_analytic_id",
    "procurement_plan_analytic_id",
]

# Fields readonly from to_submit onwards (most fields).
READONLY_STATES = {
    "to_submit": [("readonly", True)],
    "submitted": [("readonly", True)],
    "approved": [("readonly", True)],
    "done": [("readonly", True)],
    "cancelled": [("readonly", True)],
}

# Analytic dims editable in draft + to_submit only.
ANALYTIC_READONLY_STATES = {
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
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

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
            ("draft", "Draft"),
            ("to_submit", "To Submit"),
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
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        states=READONLY_STATES,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Issuing Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        states=READONLY_STATES,
    )
    payment_method_id = fields.Many2one(
        "kmitl.payment.method",
        string="Payment Method",
        required=True,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        tracking=True,
        states=FLEX_READONLY_STATES,
    )

    # --- Analytic dimensions (header-level, synced to lines) ---
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        domain=[("root_plan_id.code", "=", "funds")],
        states=ANALYTIC_READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        domain=[("root_plan_id.code", "=", "sources")],
        states=ANALYTIC_READONLY_STATES,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        domain=[("root_plan_id.code", "=", "activities")],
        states=ANALYTIC_READONLY_STATES,
    )
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="KMITL Project",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        states=ANALYTIC_READONLY_STATES,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Procurement Plan",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        states=ANALYTIC_READONLY_STATES,
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
    def get_receipt_dashboard(self):
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
        groups = self.read_group(
            [("state", "in", ["to_submit", "submitted", "approved", "done"])],
            ["amount_total"],
            ["state"],
            lazy=False,
        )
        state_map = {
            "to_submit": "to_report",
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
            lambda r: r.state == "to_submit"
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
    def _build_analytic_distribution(self):
        self.ensure_one()
        dist = {}
        for fname in ANALYTIC_DIMENSION_FIELDS:
            account = self[fname]
            if account:
                dist[str(account.id)] = 100.0
        return dist or False

    def _sync_analytic_to_lines(self):
        for rec in self:
            dist = rec._build_analytic_distribution()
            if rec.line_ids:
                rec.line_ids.write({"analytic_distribution": dist})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_analytic_to_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ANALYTIC_DIMENSION_FIELDS):
            self._sync_analytic_to_lines()
        return res

    @api.onchange(
        "department_analytic_id", "fund_analytic_id", "source_analytic_id",
        "activity_analytic_id", "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
    )
    def _onchange_analytic_dimensions(self):
        dist = self._build_analytic_distribution()
        for line in self.line_ids:
            line.analytic_distribution = dist

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange("date")
    def _onchange_date(self):
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", self.date),
                    ("date_to", ">=", self.date),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                self.account_fiscal_year_id = fiscal_year

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
        if self.account_fiscal_year_id:
            return self.account_fiscal_year_id.date_to.year + 543
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
                    "company_id": False,
                }
            )
        return seq

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_to_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft receipts can be submitted."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line before submitting."))
            for line in rec.line_ids:
                if not line.account_id:
                    raise ValidationError(
                        _("Line '%s' has no income account.") % (line.name or "")
                    )
                if line.amount <= 0:
                    raise ValidationError(
                        _("Line '%s' must have a positive amount.")
                        % (line.name or "")
                    )
            if not rec.partner_id:
                rec.partner_id = rec._default_partner_id()
            if not rec.customer_name and rec.partner_id:
                rec._sync_customer_snapshot()
            if rec.name == "/" or not rec.name:
                seq = rec._get_receipt_sequence()
                rec.name = seq.next_by_id()
            rec.state = "to_submit"
        return True

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
            rec.state = "cancelled"
        return True

    def action_draft(self):
        for rec in self:
            if rec.state not in ("to_submit", "cancelled"):
                raise UserError(
                    _("Only 'To Submit' or cancelled receipts can be "
                      "reset to draft.")
                )
            if rec.remittance_id:
                raise UserError(
                    _("Receipt %s is in remittance %s; detach it or "
                      "reset the remittance first.")
                    % (rec.name, rec.remittance_id.display_name)
                )
            rec.state = "draft"
        return True

    def action_detach(self):
        for rec in self:
            if not rec.remittance_id:
                raise UserError(_("This receipt is not in any remittance."))
            if rec.remittance_id.state not in ("draft", "submitted"):
                raise UserError(
                    _("Receipts can only be detached from draft or "
                      "submitted remittances.")
                )
            remittance = rec.remittance_id
            rec.write({"remittance_id": False, "state": "to_submit"})
            remittance.message_post(
                body=_("Receipt %s detached from this remittance.") % rec.name
            )
            rec.message_post(
                body=_("Detached from remittance %s.") % remittance.name
            )
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

    @api.model
    def action_print_receipt(self, receipt_id, is_copy=False):
        receipt = self.browse(receipt_id)
        receipt.ensure_one()
        label = _("Copy printed") if is_copy else _("Original printed")
        receipt.message_post(body=label)
        html = self.env["ir.actions.report"].with_context(
            receipt_copy=is_copy,
        )._render_qweb_html(
            "receipt_kmitl.action_report_receipt_kmitl", receipt.ids
        )[0]
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        return {"html": html}

    def unlink(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(
                    _("Only cancelled receipts can be deleted.")
                )
        return super().unlink()
