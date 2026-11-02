from odoo import fields, models
from odoo.tools import formatLang


class ApprovalRequestLine(models.Model):
    _inherit = "approval.request.line"

    disbursement_expense_ids = fields.One2many(
        "disbursement.request.approval.expense",
        "approval_request_line_id",
        string="ค่าใช้จ่ายที่ขอเบิก",
    )

    def _disbursement_figures(self):
        """``{line id: (disbursed, in progress)}`` from the Expense breakdown
        of the non-cancelled ใบขอเบิก, read as superuser: an amount counts as
        disbursed once its ใบขอเบิก consumed the budget."""
        figures = {}
        for line in self.sudo():
            disbursed = in_progress = 0.0
            for row in line.disbursement_expense_ids:
                dr = row.request_id
                # Rows left on a ใบขอเบิก re-pointed at another request (or
                # none) no longer draw this Expense.
                if dr.state == "cancel" or dr.approval_request_id != line.request_id:
                    continue
                if dr.budget_consumed_amount:
                    disbursed += row.amount
                else:
                    in_progress += row.amount
            figures[line.id] = (disbursed, in_progress)
        return figures

    def name_get(self):
        """In the ใบขอเบิก's Expense picker, show what each Expense has left."""
        if not self.env.context.get("approval_line_show_remaining"):
            return super().name_get()
        figures = self._disbursement_figures()
        result = []
        for line in self:
            disbursed, in_progress = figures.get(line.id, (0.0, 0.0))
            remaining = line.total_amount - disbursed - in_progress
            label = line.name or ""
            if line.description:
                label = "%s — %s" % (label, line.description.splitlines()[0])
            result.append(
                (
                    line.id,
                    "%s (คงเหลือ %s)"
                    % (
                        label,
                        formatLang(self.env, remaining, currency_obj=line.currency_id),
                    ),
                )
            )
        return result
