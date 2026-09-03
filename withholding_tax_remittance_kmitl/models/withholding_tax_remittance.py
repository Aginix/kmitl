# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import calendar
import json
from datetime import date

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formatLang

from odoo.addons.l10n_th_account_tax.models.withholding_tax_cert import (
    INCOME_TAX_FORM,
)
from odoo.addons.thai_date_utils.models.thai_date_mixin import (
    MONTHS_TH,
    MONTHS_TH_SHORT,
)

PND_FORM_TH = {
    "pnd1": "ภ.ง.ด.1",
    "pnd2": "ภ.ง.ด.2",
    "pnd3": "ภ.ง.ด.3",
    "pnd3a": "ภ.ง.ด.3ก",
    "pnd53": "ภ.ง.ด.53",
}


class WithholdingTaxRemittance(models.Model):
    _name = "withholding.tax.remittance"
    _description = "WHT Remittance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_remit desc, id desc"

    name = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    income_tax_form = fields.Selection(
        selection=INCOME_TAX_FORM,
        string="ภ.ง.ด.",
        required=True,
        tracking=True,
    )
    date_remit = fields.Date(
        string="Remittance Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    period_month = fields.Selection(
        selection=[(str(m), MONTHS_TH[m]) for m in range(1, 13)],
        string="เดือนภาษี",
        required=True,
        tracking=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    period_year = fields.Selection(
        selection="_get_period_year_selection",
        string="ปี (พ.ศ.)",
        required=True,
        tracking=True,
        default=lambda self: str(fields.Date.context_today(self).year + 543),
    )
    period = fields.Char(
        string="งวด",
        compute="_compute_period",
    )
    date_from = fields.Date(compute="_compute_period_range")
    date_to = fields.Date(compute="_compute_period_range")
    bank_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Bank Account",
        domain="[('account_type', '=', 'asset_cash'), ('company_id', '=', company_id)]",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Payee",
        default=lambda self: self._default_partner_id(),
    )
    cheque_no = fields.Char(string="Cheque No.")
    rd_ref = fields.Char(string="RD Reference")
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal_id(),
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    cert_ids = fields.One2many(
        comodel_name="withholding.tax.cert",
        inverse_name="remittance_id",
        string="WHT Certificates",
        copy=False,
    )
    wht_account_id = fields.Many2one(
        comodel_name="account.account",
        string="WHT Payable Account",
        compute="_compute_wht_account_id",
        store=True,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    @api.model
    def _default_partner_id(self):
        return self.env["res.partner"].search(
            [("name", "=ilike", "กรมสรรพากร")], limit=1
        )

    @api.model
    def _default_journal_id(self):
        return self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

    @api.model
    def _get_period_year_selection(self):
        base = fields.Date.context_today(self).year + 543
        return [(str(y), str(y)) for y in range(base - 3, base + 2)]

    @api.depends("period_month", "period_year")
    def _compute_period(self):
        for rec in self:
            if not (rec.period_month and rec.period_year):
                rec.period = ""
                continue
            rec.period = "%s %s" % (
                MONTHS_TH_SHORT[int(rec.period_month)],
                rec.period_year,
            )

    @api.depends("period_month", "period_year")
    def _compute_period_range(self):
        for rec in self:
            if not (rec.period_month and rec.period_year):
                rec.date_from = False
                rec.date_to = False
                continue
            ce_year = int(rec.period_year) - 543
            month = int(rec.period_month)
            last_day = calendar.monthrange(ce_year, month)[1]
            rec.date_from = date(ce_year, month, 1)
            rec.date_to = date(ce_year, month, last_day)

    @api.depends("cert_ids.wht_line.wht_tax_id.account_id")
    def _compute_wht_account_id(self):
        for rec in self:
            accounts = rec.cert_ids.mapped("wht_line.wht_tax_id.account_id")
            rec.wht_account_id = accounts[:1]

    @api.depends("cert_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.cert_ids.mapped("amount_total"))

    @api.constrains(
        "income_tax_form", "period_month", "period_year", "company_id", "state"
    )
    def _check_unique_period(self):
        for rec in self.filtered(lambda r: r.state != "cancelled"):
            duplicate = self.search(
                [
                    ("id", "!=", rec.id),
                    ("state", "!=", "cancelled"),
                    ("company_id", "=", rec.company_id.id),
                    ("income_tax_form", "=", rec.income_tax_form),
                    ("period_month", "=", rec.period_month),
                    ("period_year", "=", rec.period_year),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("มีใบนำส่ง %(form)s งวด %(period)s อยู่แล้ว (%(name)s)")
                    % {
                        "form": PND_FORM_TH.get(
                            rec.income_tax_form, rec.income_tax_form
                        ),
                        "period": rec.period,
                        "name": duplicate.name,
                    }
                )

    @api.model
    def _validate_certs(self, certs, remittance=None):
        if not certs:
            raise UserError(_("Select at least one WHT certificate."))
        if any(cert.state != "done" for cert in certs):
            raise UserError(
                _("Only certificates in 'Done' state can be remitted.")
            )
        claimed = certs.filtered(
            lambda c: c.remittance_id and c.remittance_id != remittance
        )
        if claimed:
            raise UserError(
                _(
                    "Certificate(s) %(certs)s already belong to remittance %(remit)s."
                )
                % {
                    "certs": ", ".join(claimed.mapped("name")),
                    "remit": ", ".join(
                        sorted(set(claimed.mapped("remittance_id.name")))
                    ),
                }
            )
        forms = set(certs.mapped("income_tax_form"))
        if not all(forms):
            raise UserError(_("Set the ภ.ง.ด. form on every certificate first."))
        if len(forms) > 1:
            raise UserError(
                _("Select certificates for one ภ.ง.ด. form at a time.")
            )
        accounts = certs.mapped("wht_line.wht_tax_id.account_id")
        if not accounts:
            raise UserError(
                _("Selected certificates carry no withholding tax account.")
            )
        if len(accounts) > 1:
            raise UserError(
                _("Select certificates that share the same withholding tax account.")
            )
        if remittance:
            if forms != {remittance.income_tax_form}:
                raise UserError(
                    _("Certificates must match this remittance's ภ.ง.ด. form.")
                )
            out_of_period = certs.filtered(
                lambda c: not (remittance.date_from <= c.date <= remittance.date_to)
            )
            if out_of_period:
                raise UserError(
                    _(
                        "Certificate(s) %(certs)s fall outside period %(period)s."
                    )
                    % {
                        "certs": ", ".join(out_of_period.mapped("name")),
                        "period": remittance.period,
                    }
                )
        return accounts

    def _get_fy_be(self):
        self.ensure_one()
        return self.date_remit.year + (1 if self.date_remit.month >= 10 else 0) + 543

    def _get_sequence(self):
        self.ensure_one()
        fy_be = self._get_fy_be()
        seq_code = "withholding.tax.remittance.%s" % fy_be
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "WHT Remittance FY%s" % fy_be,
                    "code": seq_code,
                    "prefix": "WHTR/%s/" % fy_be,
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def _get_memo(self):
        self.ensure_one()
        return _("นำส่ง %s งวด %s") % (
            PND_FORM_TH.get(self.income_tax_form, ""),
            self.period,
        )

    def action_load_pending_certs(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Can only load certificates on a draft remittance.")
                )
            if not rec.income_tax_form:
                raise UserError(_("Set the ภ.ง.ด. form first."))
            certs = self.env["withholding.tax.cert"].search(
                [
                    ("company_id", "=", rec.company_id.id),
                    ("state", "=", "done"),
                    ("income_tax_form", "=", rec.income_tax_form),
                    ("remittance_id", "=", False),
                    ("date", ">=", rec.date_from),
                    ("date", "<=", rec.date_to),
                ]
            )
            if rec.wht_account_id:
                certs = certs.filtered(
                    lambda c, rec=rec: rec.wht_account_id
                    in c.wht_line.wht_tax_id.account_id
                )
            if not certs:
                raise UserError(
                    _("No unremitted certificates found for this period.")
                )
            rec.cert_ids = [(4, cert.id) for cert in certs]

    def _cert_distribution_amounts(self, cert):
        """คืน [(analytic_distribution, amount)] ของใบรับรอง

        finance_kmitl ประทับ analytic_distribution ของใบสำคัญจ่ายลงทุกบรรทัดรวมถึง
        บรรทัด WHT (finance_kmitl/models/account_payment.py) จึงอ่านกลับจากบรรทัด
        เครดิตต้นทางได้แม่นที่สุด รวมข้ามใบไม่ได้เพราะแต่ละมิติเก็บเป็น
        ``{account_id: 100.0}`` — ต้องแตกบรรทัด ยอดที่นำส่งยึดตาม
        ``cert.amount_total`` เสมอ — เกลี่ยตามสัดส่วนของบรรทัดต้นทาง แล้วโยนเศษ
        ปัดเข้ากลุ่มที่มีสัดส่วนมากที่สุด
        """
        self.ensure_one()
        lines = cert.move_id.line_ids.filtered(
            lambda l: l.wht_tax_id and l.account_id.wht_account
        )
        groups = {}
        for line in lines:
            key = json.dumps(line.analytic_distribution or {}, sort_keys=True)
            groups[key] = groups.get(key, 0.0) + (line.credit - line.debit)
        if not groups or not any(json.loads(k) for k in groups):
            dist = cert.payment_id.analytic_distribution or (
                cert.move_id.analytic_distribution
            )
            groups = (
                {json.dumps(dist, sort_keys=True): cert.amount_total}
                if dist
                else {}
            )
        if not groups or not any(json.loads(k) for k in groups):
            return []
        ordered = sorted(groups.items(), key=lambda kv: abs(kv[1]))
        total = sum(amount for _key, amount in ordered)
        result = []
        remaining = cert.amount_total
        for index, (key, amount) in enumerate(ordered):
            dist = json.loads(key)
            if index == len(ordered) - 1:
                share_amount = remaining
            else:
                share_amount = (
                    cert.currency_id.round(cert.amount_total * (amount / total))
                    if total
                    else 0.0
                )
                remaining -= share_amount
            if share_amount:
                result.append((dist, share_amount))
        return result

    def _prepare_move_line_vals(self, cert, dist, amount):
        self.ensure_one()
        memo = "%s - %s" % (self._get_memo(), cert.name)
        return [
            {
                "name": memo,
                "account_id": self.wht_account_id.id,
                "partner_id": cert.partner_id.id,
                "debit": amount,
                "credit": 0.0,
                "currency_id": self.currency_id.id,
                "analytic_distribution": dist,
            },
            {
                "name": memo,
                "account_id": self.bank_account_id.id,
                "partner_id": self.partner_id.id,
                "debit": 0.0,
                "credit": amount,
                "currency_id": self.currency_id.id,
                "analytic_distribution": dist,
            },
        ]

    def _prepare_move_vals(self, cert_amounts):
        self.ensure_one()
        line_vals = []
        for cert, amounts in cert_amounts.items():
            for dist, amount in amounts:
                line_vals.extend(self._prepare_move_line_vals(cert, dist, amount))
        return {
            "ref": self._get_memo(),
            "date": self.date_remit,
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "line_ids": [(0, 0, vals) for vals in line_vals],
        }

    def _create_move(self, cert_amounts):
        self.ensure_one()
        move = self.env["account.move"].create(self._prepare_move_vals(cert_amounts))
        move.action_post()
        return move

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft remittances can be posted."))
            self._validate_certs(rec.cert_ids, remittance=rec)
            if not rec.bank_account_id:
                raise UserError(
                    _("Set the bank account the cheque is drawn on.")
                )
            if not rec.journal_id:
                raise UserError(_("Set the journal to post to."))
            cert_amounts = {
                cert: rec._cert_distribution_amounts(cert) for cert in rec.cert_ids
            }
            missing = [
                cert.name for cert, amounts in cert_amounts.items() if not amounts
            ]
            if missing:
                raise UserError(
                    _(
                        "Certificate(s) %s have no analytic dimensions on their "
                        "source entry."
                    )
                    % ", ".join(missing)
                )
            if rec.name in (False, "/"):
                rec.name = rec._get_sequence().next_by_id()
            move = rec._create_move(cert_amounts)
            rec.write({"move_id": move.id, "state": "posted"})

    def _cancel_snapshot_body(self, reversal):
        self.ensure_one()
        total = formatLang(self.env, self.amount_total, currency_obj=self.currency_id)
        parts = [
            _("Cancelled remittance holding %(count)s certificate(s), total %(total)s.")
            % {"count": len(self.cert_ids), "total": total}
        ]
        if self.move_id:
            parts.append(_("Journal entry: %s") % self.move_id.name)
        if reversal:
            parts.append(_("Reversal entry: %s") % reversal.name)
        body = Markup("<p>%s</p>") % escape(" ".join(str(p) for p in parts))
        if self.cert_ids:
            items = Markup("").join(
                Markup("<li>%s</li>")
                % escape(
                    "%s - %s"
                    % (
                        cert.name,
                        formatLang(
                            self.env, cert.amount_total, currency_obj=self.currency_id
                        ),
                    )
                )
                for cert in self.cert_ids
            )
            body += Markup("<ul>%s</ul>") % items
        return body

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(_("Already cancelled."))
            reversal = False
            if rec.move_id:
                reversal = rec.move_id._reverse_moves(
                    default_values_list=[
                        {
                            "date": fields.Date.context_today(rec),
                            "ref": _("Reversal of: %s") % rec.move_id.name,
                        }
                    ],
                    cancel=True,
                )
            rec.message_post(body=rec._cancel_snapshot_body(reversal))
            rec.cert_ids.write({"remittance_id": False})
            rec.write({"state": "cancelled", "move_id": False})

    def action_view_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entry"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.move_id.id,
            "target": "current",
        }

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted remittances cannot be deleted."))
        return super().unlink()
