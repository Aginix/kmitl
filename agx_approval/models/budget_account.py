from odoo import fields, models


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    approval_ok = fields.Boolean(
        string="ใช้ในคำขออนุมัติ",
        default=False,
        tracking=True,
        help="If checked, this budget code can be selected on approval "
        "requests (คำขออนุมัติ), independent of Purchase OK — a code may be "
        "usable from both purchase requests and approval requests (ADR-0004).",
    )
