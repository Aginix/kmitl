from odoo import fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    institute_admin_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนบริหารสถาบัน",
        domain="[('level', '=', 4)]",
        tracking=True,
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "to_verify": [("readonly", False)],
            "to_send": [("readonly", False)],
            "returned": [("readonly", False)],
        },
    )
    performance_agreement_id = fields.Many2one(
        "project.strategic.plan",
        string="ข้อตกลงการปฏิบัติงาน",
        domain="[('level', '=', 5)]",
        tracking=True,
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "to_verify": [("readonly", False)],
            "to_send": [("readonly", False)],
            "returned": [("readonly", False)],
        },
    )
    department_plan = fields.Text(
        string="แผนกลยุทธ์/แผนบริหารส่วนงาน",
        tracking=True,
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "to_verify": [("readonly", False)],
            "to_send": [("readonly", False)],
            "returned": [("readonly", False)],
        },
    )
