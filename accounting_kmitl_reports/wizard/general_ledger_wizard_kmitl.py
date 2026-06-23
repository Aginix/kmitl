# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class GeneralLedgerReportWizardKmitl(models.TransientModel):
    """Entry-point wizard for the General Ledger.

    The menu opens this wizard (which accounts to report + the date range);
    its button then launches the OWL client action with those parameters. It
    inherits the OCA wizard to reuse its fields (``account_ids``, ``date_from``,
    ``date_to``, ``target_move``, ``company_id``); it also still serves as the
    ``ir.actions.report`` carrier for the PDF/XLSX exports.
    """

    _name = "general.ledger.report.wizard.kmitl"
    _inherit = "general.ledger.report.wizard"
    _description = "KMITL General Ledger Report (wizard)"

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
