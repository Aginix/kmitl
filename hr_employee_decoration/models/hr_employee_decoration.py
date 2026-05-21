from odoo import api, fields, models


class HrEmployeeDecoration(models.Model):
    _name = "hr.employee.decoration"
    _description = "HR Employee Decoration"
    _inherit = ["mail.thread"]

    employee_id = fields.Many2one(
        comodel_name="hr.employee", required=True, tracking=True
    )
    relation_id = fields.Many2one(
        "hr.employee.decoration.relation",
        string="Decoration",
        required=True,
        tracking=True,
    )
    decoration_level = fields.Float(
        string="Level", related="relation_id.level", store=False, readonly=True
    )
    effective_date = fields.Date(required=True, tracking=True)
    volume = fields.Char(tracking=True)
    chapter = fields.Char(tracking=True)
    published_date = fields.Date(tracking=True)
    page = fields.Integer(tracking=True)
    no = fields.Char(string="No.", tracking=True)
    department = fields.Char(string="Certified by", tracking=True)
    year = fields.Char(compute="_compute_year", store=False, readonly=True)
    office_order_id = fields.Many2one(comodel_name="office.order", tracking=True)
    order_date = fields.Date(
        string="Order Date", related="office_order_id.date", readonly=True, store=False
    )

    def name_get(self):
        return [
            (record.id, f"{record.employee_id.name} - {record.relation_id.name}")
            for record in self
        ]

    @api.depends("effective_date")
    def _compute_year(self):
        for record in self:
            record.year = ""
            if record.effective_date:
                record.year = record.effective_date.year
