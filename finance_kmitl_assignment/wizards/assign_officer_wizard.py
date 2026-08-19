# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

OFFICER_GROUP = "finance_kmitl.group_finance_kmitl_user_out"


class FinanceAssignOfficerWizard(models.TransientModel):
    # Dedicated name (not the disbursement ``disbursement.assign.officer.wizard``):
    # reusing that name would make this an implicit cross-module inherit of a
    # model we do not depend on.
    _name = "finance.assign.officer.wizard"
    _description = "Assign Finance Payment Officer"

    payment_id = fields.Many2one(
        "account.payment",
        string="Payment Voucher",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )
    allowed_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_allowed_user_ids",
    )

    @api.depends("payment_id")
    def _compute_allowed_user_ids(self):
        group = self.env.ref(OFFICER_GROUP, raise_if_not_found=False)
        users = group.users if group else self.env["res.users"]
        for wiz in self:
            wiz.allowed_user_ids = users

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("payment_id") and "user_id" in fields_list:
            payment = self.env["account.payment"].browse(res["payment_id"])
            if payment.assigned_to:
                res["user_id"] = payment.assigned_to.id
        return res

    def action_assign(self):
        self.ensure_one()
        payment = self.payment_id
        if not payment._assignment_is_manager():
            raise AccessError(_("Only a manager can assign another officer."))
        old_officer = payment.assigned_to
        payment.assigned_to = self.user_id
        if old_officer and old_officer != self.user_id:
            payment._assignment_clear_activity(old_officer)
        if self.user_id and self.user_id != self.env.user:
            payment._assignment_notify(self.user_id)
        return {"type": "ir.actions.act_window_close"}
