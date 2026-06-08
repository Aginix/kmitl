# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Operation Type",
        required=True,
    )
    to_reconcile_payment_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_payment_to_reconcile_line_rel",
        column1="payment_id",
        column2="move_line_id",
        string="Lines to Reconcile",
        copy=False,
    )
    amount_wht = fields.Monetary(
        string="Withholding Tax",
        compute="_compute_amount_wht",
        currency_field="currency_id",
        help="Total withholding tax withheld on this payment. Derived from the "
        "payment move lines carrying a WHT tax, so it is visible in every state "
        "(the native withholding moves are only created on posting).",
    )
    amount_before_wht = fields.Monetary(
        string="Amount Before Withholding",
        compute="_compute_amount_wht",
        currency_field="currency_id",
        help="Gross amount before withholding tax (net amount paid plus the "
        "withholding tax).",
    )

    @api.depends("move_id.line_ids.wht_tax_id", "move_id.line_ids.balance", "amount")
    def _compute_amount_wht(self):
        for payment in self:
            wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
            payment.amount_wht = sum(abs(line.balance) for line in wht_lines)
            payment.amount_before_wht = payment.amount + payment.amount_wht

    def action_post(self):
        """Validate bank export for outbound, then reconcile after posting."""
        for payment in self:
            if (
                payment.payment_type == "outbound"
                and payment.export_status == "draft"
            ):
                raise UserError(
                    _("Payment must be exported to bank before posting.")
                )
        res = super().action_post()
        self._reconcile_source_invoice_lines()
        return res

    def _reconcile_source_invoice_lines(self):
        """Reconcile payment lines with stored source invoice lines."""
        domain = [
            ("parent_state", "=", "posted"),
            ("account_type", "in", ("asset_receivable", "liability_payable")),
            ("reconciled", "=", False),
        ]
        for payment in self.filtered("to_reconcile_payment_line_ids"):
            payment_lines = payment.line_ids.filtered_domain(domain)
            source_lines = payment.to_reconcile_payment_line_ids
            for account in payment_lines.account_id:
                (payment_lines + source_lines).filtered_domain(
                    [("account_id", "=", account.id), ("reconciled", "=", False)]
                ).reconcile()
            payment.to_reconcile_payment_line_ids = False

    def action_submit(self):
        """Submit payment without triggering tier validation.

        Validation is triggered after bank export, not on submit. Assign the
        move sequence on submit so every payment gets a number immediately,
        instead of some staying unnamed ("Draft") until they are posted
        (the native name is only assigned for the first move of a period
        while it is unposted).
        """
        for payment in self:
            move = payment.move_id
            if move.state != "draft":
                raise UserError(_("Only draft payments can be submitted."))
            move.state = "submitted"
            if move.date and (not move.name or move.name == "/"):
                move._set_next_sequence()

    @api.onchange("kmitl_payment_type_id")
    def _onchange_kmitl_payment_type_id(self):
        if self.kmitl_payment_type_id:
            self.payment_type = self.kmitl_payment_type_id.direction
            if self.kmitl_payment_type_id.journal_id:
                self.journal_id = self.kmitl_payment_type_id.journal_id

    @api.depends("kmitl_payment_type_id")
    def _compute_destination_account_id(self):
        # Let base compute first (handles standard receivable/payable logic),
        # then override only when a custom account is explicitly configured.
        super()._compute_destination_account_id()
        for pay in self:
            ptype = pay.kmitl_payment_type_id
            if ptype and ptype.override_account_id:
                pay.destination_account_id = ptype.override_account_id

    def _seek_for_lines(self):
        """Treat override account as counterpart even if not receivable/payable.

        Base Odoo classifies lines as liquidity / counterpart / writeoff based on
        account type. When kmitl_payment_type uses a non-standard account
        (e.g. a deposit account that is neither receivable nor payable), base
        leaves counterpart_lines empty and puts that line in writeoff_lines.
        We re-classify it here so the rest of the payment logic works correctly.
        """
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        ptype = self.kmitl_payment_type_id
        # Only reclassify when base couldn't find a counterpart on its own.
        if ptype and ptype.override_account_id and not counterpart_lines:
            new_writeoff = self.env["account.move.line"]
            for line in writeoff_lines:
                if line.account_id == ptype.override_account_id:
                    counterpart_lines += line
                else:
                    new_writeoff += line
            writeoff_lines = new_writeoff
        return liquidity_lines, counterpart_lines, writeoff_lines

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Propagate analytic_distribution to all generated move lines.

        Base Odoo does not copy analytic_distribution from the payment to the
        move lines it creates (liquidity + counterpart). We propagate it here
        so analytic reporting reflects the correct distribution on both entries.

        Note: analytic_distribution lives on account.move (via _inherits), so
        writing it on the payment goes directly to the move — it does NOT go
        through _synchronize_to_moves and therefore must be pushed to lines here.
        """
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)
        if self.analytic_distribution:
            for line_vals in line_vals_list:
                line_vals["analytic_distribution"] = self.analytic_distribution
        return line_vals_list

    def _get_trigger_fields_to_synchronize(self):
        # Extend the base tuple (immutable) so that changing kmitl_payment_type_id
        # also triggers a move re-synchronization (account/journal may change).
        return (
            *super()._get_trigger_fields_to_synchronize(),
            "kmitl_payment_type_id",
        )

