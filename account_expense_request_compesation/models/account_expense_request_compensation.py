from odoo import _, api, fields, models


class AccountExpenseRequestCompensation(models.Model):

    _name = "account.expense.request.compensation"
    _inherit = ['account.expense.request']
    _description = "Account Expense Request Compensation"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    compensation_type_id = fields.Many2one(
        string="Compensation Type",
        comodel_name="account.expense.request.compensation.type",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    payment_type = fields.Selection(
        string="Payment Type",
        selection=[("direct", "Direct paid"), ("loan", "Loan"), ("prepaid", "Prepaid")],
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    line_ids = fields.One2many(
        string="Request Lines",
        comodel_name="account.expense.request.compensation.line",
        inverse_name="request_id",
        copy=True,
        states=READONLY_STATES,
    )

    can_edit_type = fields.Boolean(
        string="Can Edit Type",
        compute="_compute_can_edit_type",
    )

    @api.depends("line_ids")
    def _compute_can_edit_type(self):
        for record in self:
            if record.line_ids.ids:
                record.can_edit_type = False
            else:
                record.can_edit_type = True

    @api.onchange("compensation_type_id")
    def _onchange_compensation_type_id(self):
        self.line_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.expense.request.compensation"
                ) or "/"

        return super().create(vals_list)
