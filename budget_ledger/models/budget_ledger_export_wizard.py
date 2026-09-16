from odoo import fields, models


class BudgetLedgerExportWizard(models.TransientModel):
    """Throwaway carrier for the XLSX report action.

    ``report_action`` needs a concrete record to render against; the real
    filters travel in the report ``data`` dict (see
    ``budget.ledger.action_export_xlsx``), so this holds only a reference to the
    fiscal year for context.
    """

    _name = "budget.ledger.export.wizard"
    _description = "Budget Ledger XLSX Export Carrier"

    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year", string="ปีงบประมาณ"
    )
