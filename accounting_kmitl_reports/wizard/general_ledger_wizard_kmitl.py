# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class GeneralLedgerReportWizardKmitl(models.TransientModel):
    """Entry-point wizard for the General Ledger.

    The menu opens this wizard (which accounts to report + the period); its
    button then launches the OWL client action with those parameters. It
    inherits the OCA wizard to reuse its fields (``account_ids``, ``date_from``,
    ``date_to``, ``target_move``, ``company_id``); it also still serves as the
    ``ir.actions.report`` carrier for the PDF/XLSX exports.

    The period is driven by a Fiscal Year selector that defaults to the
    current fiscal year and fills the date range (still editable afterwards).
    """

    _name = "general.ledger.report.wizard.kmitl"
    _inherit = "general.ledger.report.wizard"
    _description = "KMITL General Ledger Report (wizard)"

    fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        default=lambda self: self._kmitl_default_fiscal_year(),
    )

    def _kmitl_default_fiscal_year(self):
        """The fiscal year covering today (else the most recent one)."""
        today = fields.Date.context_today(self)
        company = self.env.company
        FiscalYear = self.env["account.fiscal.year"]
        fy = FiscalYear.search(
            [
                ("company_id", "=", company.id),
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ],
            limit=1,
        )
        if not fy:
            fy = FiscalYear.search(
                [("company_id", "=", company.id)], order="date_from desc", limit=1
            )
        return fy

    @api.onchange("fiscal_year_id")
    def _onchange_fiscal_year_id(self):
        """Selecting a fiscal year fills the date range (the dates stay
        editable for an ad-hoc period)."""
        if self.fiscal_year_id:
            self.date_from = self.fiscal_year_id.date_from
            self.date_to = self.fiscal_year_id.date_to

    def action_view_general_ledger(self):
        """Open the General Ledger OWL report for the chosen accounts/period.
        Parameters travel in the action ``params`` (read by the client action)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "kmitl_general_ledger",
            "name": _("General Ledger"),
            "params": {
                "company_id": self.company_id.id,
                "account_ids": self.account_ids.ids,
                "date_from": fields.Date.to_string(self.date_from),
                "date_to": fields.Date.to_string(self.date_to),
                "only_posted": self.target_move == "posted",
            },
        }
