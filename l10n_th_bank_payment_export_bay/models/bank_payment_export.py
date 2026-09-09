# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank = fields.Selection(
        selection_add=[("AYUDTHBK", "BAY")],
        ondelete={"AYUDTHBK": "cascade"},
    )
    # Configuration
    bay_company_id = fields.Char(
        string="BAY Company ID",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    bay_sender_name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Not written into the file. CashLink leaves the twenty characters "
        "after the originating account empty -- every file KMITL sends the bank "
        "does -- and a name written there is the only structural difference "
        "between a file the bank took and one it refused with 'user account "
        "product linkage is not available'. Kept only because the form has "
        "always offered it.",
    )
    # filter
    bay_is_editable = fields.Boolean(
        compute="_compute_bay_editable",
        string="BAY Editable",
    )
    bay_service_type = fields.Selection(
        selection=[
            ("01", "01 - Salary, Wages, Gratuity, Pension"),
            ("02", "02 - Dividend"),
            ("03", "03 - Interest"),
            ("04", "04 - Goods and Services"),
            ("05", "05 - Sale of Securities"),
            ("06", "06 - Tax Refund"),
            ("07", "07 - Loan"),
            ("59", "59 - Other"),
        ],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.depends("bank")
    def _compute_required_effective_date(self):
        res = super()._compute_required_effective_date()
        for rec in self.filtered(lambda export: export.bank == "AYUDTHBK"):
            rec.is_required_effective_date = True
        return res

    @api.depends("bank")
    def _compute_bay_editable(self):
        for export in self:
            export.bay_is_editable = True if export.bank == "AYUDTHBK" else False

    def _check_constraint_line(self):
        res = super()._check_constraint_line()
        self.ensure_one()
        if self.bank == "AYUDTHBK":
            for line in self.export_line_ids:
                if not line.payment_partner_bank_id:
                    raise UserError(
                        _("Recipient Bank with {} is not selected.").format(
                            line.payment_id.name
                        )
                    )
        return res
