from odoo import api, fields, models


class BudgetTransferVerifyReturnWizard(models.TransientModel):
    _inherit = "budget.transfer.verify.return.wizard"

    reason = fields.Text(required=False)
    outstanding_requests = fields.Text(
        string="ข้อขอแก้ไขที่ค้างอยู่",
        compute="_compute_outstanding_requests",
    )

    @api.depends("transfer_id")
    def _compute_outstanding_requests(self):
        for wizard in self:
            wizard.outstanding_requests = (
                "\n".join(wizard.transfer_id._outstanding_change_request_lines())
                if wizard.transfer_id
                else False
            )
