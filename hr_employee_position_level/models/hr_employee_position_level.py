from odoo import fields, models


class HrEmployeePositionLevel(models.Model):
    _name = "hr.employee.position.level"
    _description = "HR Employee Position Level"

    name = fields.Char(
        string="Name", related="relation_id.name", readonly=True, store=False
    )
    employee_id = fields.Many2one(comodel_name="hr.employee", required=True)
    relation_id = fields.Many2one("hr.employee.position.level.relation", required=True)
    office_order_id = fields.Many2one(comodel_name="office.order")
    level = fields.Float(
        string="Level", related="relation_id.level", readonly=True, store=False
    )
    effective_date = fields.Date()
    order_date = fields.Date(
        string="Order Date", related="office_order_id.date", readonly=True, store=False
    )
    discipline_id = fields.Many2one(comodel_name="resource.academic.discipline")
    subdiscipline_id = fields.Many2one(comodel_name="resource.academic.discipline")
