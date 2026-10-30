from odoo import api, fields, models


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    debit = fields.Float(
        string="เดบิต",
        digits="Budget Precision",
        compute="_compute_debit_credit",
        store=True,
        help="จำนวนเงินฝั่งเดบิต (รายการจัดสรรงบประมาณปกติ)",
    )
    credit = fields.Float(
        string="เครดิต",
        digits="Budget Precision",
        compute="_compute_debit_credit",
        store=True,
        help="จำนวนเงินฝั่งเครดิต (รายการหักโอน)",
    )

    @api.depends("balance", "deduct")
    def _compute_debit_credit(self):
        for line in self:
            if line.deduct:
                line.debit = 0.0
                line.credit = line.balance
            else:
                line.debit = line.balance
                line.credit = 0.0
