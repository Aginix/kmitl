from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):

    _name = "approval.request"
    _description = "Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "billed": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }

    category_id = fields.Many2one(
        string="Category",
        comodel_name="approval.category",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    department_id = fields.Many2one(
        string="Department",
        comodel_name="hr.department",
        default=lambda self: self.env.user.employee_id.department_id,
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    name = fields.Char(
        string="Name",
        default="/",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    date = fields.Date(
        string="Date",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    request_owner_id = fields.Many2one(
        string="Request Owner",
        comodel_name="res.partner",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    responsible_id = fields.Many2one(
        string="Responsible Person",
        comodel_name="res.partner",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    description = fields.Text(
        string="Description",
        tracking=True,
        states=READONLY_STATES,
    )

    date_start = fields.Date(
        string="Date Start",
        tracking=True,
        states=READONLY_STATES,
    )

    date_end = fields.Date(
        string="Date End",
        tracking=True,
        states=READONLY_STATES,
    )

    city = fields.Char(
        string="City",
        tracking=True,
        states=READONLY_STATES,
    )

    country_id = fields.Many2one(
        string="Country",
        comodel_name="res.country",
        tracking=True,
        states=READONLY_STATES,
    )

    line_ids = fields.One2many(
        "approval.request.line",
        "request_id",
        string="Expense Lines",
        states=READONLY_STATES,
    )

    has_period = fields.Boolean(
        related='category_id.has_period'
    )

    has_city = fields.Boolean(
        related='category_id.has_city'
    )

    has_country_id = fields.Boolean(
        related='category_id.has_country_id'
    )

    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("validated", "Validated"),
        ("approved", "Approved"),
        ("billed", "Billed"),
        ("cancelled", "Cancelled"),
    ],
        default="draft",
        string="state"
    )

    @api.onchange("category_id")
    def _onchange_category_id(self):
        self.line_ids = False

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            record.state = "submitted"
        return True

    def action_validate(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be validated."))
            record.state = "validated"
        return True

    def action_cancel(self):
        for record in self:
            if record.state == "cancel":
                raise UserError(_("Request is already cancelled."))
            record.state = "cancel"
        return True

    def action_draft(self):
        for record in self:
            record.state = "draft"
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "approval.request"
                ) or "/"

        return super().create(vals_list)
