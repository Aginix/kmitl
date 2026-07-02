# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ChequeRegister(models.Model):
    _name = "cheque.register"
    _description = "Cheque Control Register"
    _inherit = ["mail.thread", "mail.activity.mixin", "thai.date.mixin"]
    _order = "cheque_date desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    direction = fields.Selection(
        selection=[
            ("outbound", "Issued Cheque"),
            ("inbound", "Received Cheque"),
        ],
        string="Direction",
        required=True,
        default=lambda self: self.env.context.get("default_direction", "outbound"),
        tracking=True,
    )
    cheque_number = fields.Char(string="Cheque No.", tracking=True)
    cheque_date = fields.Date(
        string="Cheque Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Bank/Cheque Book",
        domain="[('type', 'in', ('bank', 'cash'))]",
        tracking=True,
    )
    bank_id = fields.Many2one(
        comodel_name="res.bank",
        related="journal_id.bank_id",
        string="Bank",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Payee/Drawer",
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount", currency_field="currency_id", tracking=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    ref = fields.Char(string="Source Document")
    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        ondelete="set null",
        index=True,
        copy=False,
        readonly=True,
    )
    handover_date = fields.Date(string="Handover/Receipt Date", tracking=True)
    deposit_date = fields.Date(string="Deposit Date", tracking=True)
    clearing_date = fields.Date(string="Clearing Date", tracking=True)
    note = fields.Text(string="Notes")
    crossed = fields.Boolean(
        string="A/C Payee Only",
        default=True,
        help="Print the 'A/C PAYEE ONLY' crossing when printing the cheque.",
    )
    strike_bearer = fields.Boolean(
        string="Strike 'or Bearer'",
        default=True,
        help="Strike out the pre-printed 'หรือผู้ถือ' (or bearer) wording when "
        "printing the cheque.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Outstanding"),
            ("cleared", "Cleared"),
            ("bounced", "Bounced"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                direction = vals.get("direction") or self.env.context.get(
                    "default_direction", "outbound"
                )
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "cheque.register.%s" % direction
                ) or _("New")
        return super().create(vals_list)

    @api.constrains("cheque_number", "journal_id", "direction", "company_id")
    def _check_unique_outbound_number(self):
        """Issued cheques must keep consecutive, non-repeating numbers per cheque
        book. A cancelled cheque still occupies its number (never reused). Received
        cheques carry numbers from external banks, so no uniqueness is enforced."""
        for cheque in self:
            if cheque.direction != "outbound" or not cheque.cheque_number:
                continue
            duplicate = self.search_count(
                [
                    ("id", "!=", cheque.id),
                    ("direction", "=", "outbound"),
                    ("cheque_number", "=", cheque.cheque_number),
                    ("journal_id", "=", cheque.journal_id.id),
                    ("company_id", "=", cheque.company_id.id),
                ]
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "Cheque number %(num)s already exists in this cheque book.",
                        num=cheque.cheque_number,
                    )
                )

    @api.constrains("state", "cheque_number")
    def _check_cheque_number_required(self):
        """A draft row may pre-exist (e.g. auto-created from a payment) before the
        physical cheque number is known; the number becomes mandatory once the
        cheque is issued/received."""
        for cheque in self:
            if cheque.state != "draft" and not cheque.cheque_number:
                raise ValidationError(
                    _("A cheque number is required before the cheque can be issued.")
                )

    def action_activate(self):
        for cheque in self:
            if cheque.state != "draft":
                raise UserError(_("Only draft cheques can be issued/received."))
            cheque.write(
                {
                    "state": "active",
                    "handover_date": cheque.handover_date
                    or fields.Date.context_today(cheque),
                }
            )

    def action_clear(self):
        for cheque in self:
            if cheque.state != "active":
                raise UserError(_("Only outstanding cheques can be cleared."))
            cheque.write(
                {
                    "state": "cleared",
                    "clearing_date": cheque.clearing_date
                    or fields.Date.context_today(cheque),
                }
            )

    def action_bounce(self):
        for cheque in self:
            if cheque.state != "active":
                raise UserError(_("Only outstanding cheques can bounce."))
            cheque.state = "bounced"

    def action_cancel(self):
        for cheque in self:
            if cheque.state == "cleared":
                raise UserError(_("Cleared cheques cannot be cancelled."))
            cheque.state = "cancelled"

    def action_reset_draft(self):
        self.write({"state": "draft"})

    # ------------------------------------------------------------------
    # Cheque printing
    # ------------------------------------------------------------------
    def amount_in_words(self):
        """Amount spelled out in Thai baht text (for the cheque)."""
        self.ensure_one()
        return self.currency_id.with_context(lang="th_TH").amount_to_text(
            self.amount
        )

    def date_digits(self, buddhist_year=False):
        """Return the cheque date as ``DDMMYYYY`` digits for the date boxes."""
        self.ensure_one()
        if not self.cheque_date:
            return ""
        d = self.cheque_date
        year = d.year + 543 if buddhist_year else d.year
        return "%02d%02d%04d" % (d.day, d.month, year)

    def action_print_cheque(self):
        self.ensure_one()
        if not self.cheque_number:
            raise UserError(_("Enter the cheque number before printing."))
        if not self.journal_id:
            raise UserError(
                _("Select the bank/cheque book (journal) before printing.")
            )
        if not self.journal_id.cheque_layout_id:
            raise UserError(
                _(
                    "Configure a Cheque Layout on journal '%s' before printing.",
                )
                % self.journal_id.display_name
            )
        return self.env.ref(
            "finance_kmitl.action_report_cheque_print"
        ).report_action(self)
