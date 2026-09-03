# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_th_account_tax.models.withholding_tax_cert import (
    INCOME_TAX_FORM,
)
from odoo.addons.thai_date_utils.models.thai_date_mixin import MONTHS_TH_SHORT

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
    period = fields.Char(
        string="งวด",
        compute="_compute_period",
    )
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

    @api.depends("cert_ids.date")
    def _compute_period(self):
        for rec in self:
            dates = rec.cert_ids.mapped("date")
            if not dates:
                rec.period = ""
                continue
            months = sorted({(d.year, d.month) for d in dates})
            first = "%s %s" % (MONTHS_TH_SHORT[months[0][1]], months[0][0] + 543)
            if len(months) == 1:
                rec.period = first
            else:
                last = "%s %s" % (MONTHS_TH_SHORT[months[-1][1]], months[-1][0] + 543)
                rec.period = "%s - %s" % (first, last)

    @api.depends("cert_ids.wht_line.wht_tax_id.account_id")
    def _compute_wht_account_id(self):
        for rec in self:
            accounts = rec.cert_ids.mapped("wht_line.wht_tax_id.account_id")
            rec.wht_account_id = accounts[:1]

    @api.depends("cert_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.cert_ids.mapped("amount_total"))

    @api.model
    def _validate_certs(self, certs):
        if not certs:
            raise UserError(_("Select at least one WHT certificate."))
        if any(cert.state != "done" for cert in certs):
            raise UserError(
                _("Only certificates in 'Done' state can be remitted.")
            )
        if any(cert.remit_state != "pending" for cert in certs):
            raise UserError(_("Selected certificates are already remitted."))
        if len(set(certs.mapped("income_tax_form"))) > 1:
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
                    ("remit_state", "=", "pending"),
                    ("income_tax_form", "=", rec.income_tax_form),
                ]
            )
            if rec.wht_account_id:
                certs = certs.filtered(
                    lambda c, rec=rec: rec.wht_account_id
                    in c.wht_line.wht_tax_id.account_id
                )
            if not certs:
                raise UserError(
                    _("No unremitted certificates found for this form.")
                )
            rec.cert_ids = [(4, cert.id) for cert in certs]

    def _prepare_debit_line_vals(self):
        self.ensure_one()
        return {
            "name": self._get_memo(),
            "account_id": self.wht_account_id.id,
            "partner_id": self.partner_id.id,
            "debit": self.amount_total,
            "credit": 0.0,
            "currency_id": self.currency_id.id,
        }

    def _prepare_credit_line_vals(self):
        self.ensure_one()
        return {
            "name": self._get_memo(),
            "account_id": self.bank_account_id.id,
            "partner_id": self.partner_id.id,
            "debit": 0.0,
            "credit": self.amount_total,
            "currency_id": self.currency_id.id,
        }

    def _prepare_move_vals(self):
        self.ensure_one()
        return {
            "ref": self._get_memo(),
            "date": self.date_remit,
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "line_ids": [
                (0, 0, self._prepare_debit_line_vals()),
                (0, 0, self._prepare_credit_line_vals()),
            ],
        }

    def _create_move(self):
        self.ensure_one()
        move = self.env["account.move"].create(self._prepare_move_vals())
        move.action_post()
        return move

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft remittances can be posted."))
            self._validate_certs(rec.cert_ids)
            if not rec.bank_account_id:
                raise UserError(
                    _("Set the bank account the cheque is drawn on.")
                )
            if not rec.journal_id:
                raise UserError(_("Set the journal to post to."))
            if rec.name in (False, "/"):
                rec.name = rec._get_sequence().next_by_id()
            move = rec._create_move()
            rec.write({"move_id": move.id, "state": "posted"})

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(_("Already cancelled."))
            if rec.move_id:
                rec.move_id._reverse_moves(
                    default_values_list=[
                        {
                            "date": fields.Date.context_today(rec),
                            "ref": _("Reversal of: %s") % rec.move_id.name,
                        }
                    ],
                    cancel=True,
                )
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
