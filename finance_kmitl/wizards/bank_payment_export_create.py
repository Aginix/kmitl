# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BankPaymentExportCreate(models.TransientModel):
    """Turn a selection of vouchers into e-payment files.

    One file debits one account, so a selection is not one batch but as many as it
    has หัวจ่าย. This shows the officer the split it is about to make — and, where
    an account already has a draft file, asks whether these vouchers join it — so
    that ending up with four files reads as the rule rather than a surprise.
    """

    _name = "bank.payment.export.create"
    _description = "Create e-Payment File"

    line_ids = fields.One2many(
        comodel_name="bank.payment.export.create.line",
        inverse_name="wizard_id",
        string="Files to create",
    )

    def action_create(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("There is nothing to put in a file."))
        exports = self.env["bank.payment.export"]
        for line in self.line_ids:
            exports |= line._apply()
        return exports._action_open_created()


class BankPaymentExportCreateLine(models.TransientModel):
    """One paying account's worth of the selection — that is, one file."""

    _name = "bank.payment.export.create.line"
    _description = "Create e-Payment File Line"

    wizard_id = fields.Many2one(
        comodel_name="bank.payment.export.create",
        required=True,
        ondelete="cascade",
    )
    paying_account_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Paying Account",
        required=True,
        readonly=True,
    )
    bank_id = fields.Many2one(
        related="paying_account_id.bank_id",
        string="Bank",
        readonly=True,
    )
    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="Payment Vouchers",
        readonly=True,
    )
    payment_count = fields.Integer(
        compute="_compute_payment_totals",
        string="Vouchers",
    )
    amount_total = fields.Monetary(
        compute="_compute_payment_totals",
        string="Total",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_payment_totals",
    )
    destination = fields.Selection(
        selection=[
            ("new", "A new file"),
            ("existing", "An existing draft file"),
        ],
        string="Put them in",
        default="new",
        required=True,
    )
    available_export_ids = fields.Many2many(
        comodel_name="bank.payment.export",
        compute="_compute_available_export_ids",
        string="Draft files on this account",
    )
    payment_export_id = fields.Many2one(
        comodel_name="bank.payment.export",
        string="Draft File",
        domain="[('id', 'in', available_export_ids)]",
    )
    payment_export_effective_date = fields.Date(
        related="payment_export_id.effective_date",
        string="Effective Date",
        readonly=True,
    )
    payment_export_count = fields.Integer(
        related="payment_export_id.export_line_count",
        string="Rows already in it",
        readonly=True,
    )

    @api.depends("payment_ids")
    def _compute_payment_totals(self):
        for line in self:
            line.payment_count = len(line.payment_ids)
            line.currency_id = line.payment_ids[:1].currency_id
            line.amount_total = sum(line.payment_ids.mapped("amount"))

    @api.depends("paying_account_id")
    def _compute_available_export_ids(self):
        for line in self:
            line.available_export_ids = self.env["bank.payment.export"].search(
                [
                    ("state", "=", "draft"),
                    ("paying_account_id", "=", line.paying_account_id.id),
                ]
            )

    @api.onchange("destination", "available_export_ids")
    def _onchange_destination(self):
        for line in self:
            if line.destination != "existing":
                line.payment_export_id = False
            elif len(line.available_export_ids) == 1:
                line.payment_export_id = line.available_export_ids

    def _apply(self):
        """Create the file, or add these vouchers to the chosen draft one."""
        self.ensure_one()
        if self.destination == "existing":
            if not self.payment_export_id:
                raise UserError(
                    _("Choose which draft file the %s vouchers go into.")
                    % self.paying_account_id.display_name
                )
            # Re-read now, not when the wizard was built: the list of candidates was
            # filtered to drafts at that moment, and a colleague can confirm or even
            # export the chosen file while this dialog sits open. Rows added then
            # would land in a file that has already gone to the bank.
            if self.payment_export_id.state != "draft":
                raise UserError(
                    _(
                        "%s is no longer a draft, so nothing more can be added to "
                        "it. Create a new file for these vouchers instead."
                    )
                    % self.payment_export_id.display_name
                )
            self.env["bank.payment.export.line"].create(
                [
                    {
                        "payment_export_id": self.payment_export_id.id,
                        "payment_id": payment.id,
                    }
                    for payment in self.payment_ids
                ]
            )
            return self.payment_export_id
        return self.env["bank.payment.export"].create(self._prepare_export_vals())

    def _prepare_export_vals(self):
        """The file this line stands for.

        No effective date: that is the one thing about the file nobody can read off
        the vouchers — it is what the office decides the bank should move the money
        on, and it is what dates the withholding-tax certificates.
        """
        self.ensure_one()
        exports = self.env["bank.payment.export"]
        payment = self.payment_ids[:1]
        vals = {
            "paying_account_id": self.paying_account_id.id,
            "template_id": payment.bank_payment_template_id.id,
            "company_id": payment.company_id.id,
            "currency_id": payment.currency_id.id,
            "export_line_ids": [
                (0, 0, {"payment_id": each.id}) for each in self.payment_ids
            ],
        }
        vals.update(
            exports._prepare_bank_vals_from_paying_account(self.paying_account_id)
        )
        return vals
