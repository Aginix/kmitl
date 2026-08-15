from odoo import _, fields, models


class BudgetTransferRejectWizard(models.TransientModel):
    """
    Wizard for rejecting budget transfers with reason
    """
    
    _name = "budget.transfer.reject.wizard"
    _description = "Budget Transfer Rejection Wizard"
    
    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        string="Budget Transfer",
        required=True,
        readonly=True,
    )
    
    rejection_reason = fields.Text(
        string="Rejection Reason",
        required=True,
        help="Please provide detailed reason for rejecting this budget transfer"
    )
    
    def action_reject(self):
        """Reject the transfer with provided reason"""
        self.ensure_one()
        
        self.transfer_id.write({
            "state": "rejected",
            "rejection_reason": self.rejection_reason,
            "approver_id": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })
        
        # Send rejection email notification
        template = self.env.ref("budget_transfer.email_template_budget_transfer_rejected")
        if template and self.transfer_id.user_id.email:
            template.with_context(lang=self.transfer_id.user_id.lang).send_mail(
                self.transfer_id.id,
                email_values={"email_to": self.transfer_id.user_id.email},
                force_send=True
            )
        
        # Send rejection notification in chatter
        self.transfer_id.message_post(
            body=_("Budget transfer rejected by {} with reason: {}").format(
                self.env.user.name, 
                self.rejection_reason
            ),
            partner_ids=[self.transfer_id.user_id.partner_id.id],
            message_type="notification"
        )
        
        return {"type": "ir.actions.act_window_close"}