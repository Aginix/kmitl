from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ConstructionProject(models.Model):

    _name = "construction.project"
    _description = "Construction Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    READONLY_STATES = {
        "in_progress": [("readonly", True)],
        "ended": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }

    ref = fields.Char(string="Reference", default="/", readonly=True, copy=False)

    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
        states=READONLY_STATES,
    )

    name = fields.Char(string="Name", required=True, states=READONLY_STATES)

    date_end = fields.Date(string="End Date", readonly=True)

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="project_id",
        string="Purchase Requests",
    )

    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="Purchase Orders",
        compute="_compute_purchase_order_ids",
    )

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        related='purchase_request_ids.main_sarabun_document_id'
    )

    def _compute_purchase_order_ids(self):
        for record in self:
            record.purchase_order_ids = record.purchase_request_ids.mapped(
                "line_ids.purchase_lines.order_id"
            )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("ended", "Ended"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        required=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ref", "/") == "/":
                vals["ref"] = self.env["ir.sequence"].next_by_code(
                    "construction.project"
                ) or "/"
        return super().create(vals_list)

    def action_start(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft projects can be started."))
            record.state = "in_progress"

    def action_end(self):
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("Only in-progress projects can be ended."))
        not_done = self.purchase_request_ids.filtered(lambda r: r.state != "done")
        if not_done:
            raise UserError(
                _("All purchase requests must be done before ending the project.")
            )
        return {
            "name": _("End Construction Project"),
            "type": "ir.actions.act_window",
            "res_model": "construction.project.end.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_cancel(self):
        for record in self:
            if record.state == "cancelled":
                raise UserError(_("Project is already cancelled."))
            record.state = "cancelled"

    def action_draft(self):
        for record in self:
            record.state = "draft"
