from odoo import api, fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    organizer_department_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงานผู้จัดโครงการ",
        compute="_compute_organizer_department_id",
        store=True,
        readonly=False,
        index=True,
        tracking=True,
        domain=[("root_plan_id.code", "=", "departments")],
        states={
            "draft": [("readonly", False)],
            "to_verify": [("readonly", False)],
            "to_send": [("readonly", False)],
            "returned": [("readonly", False)],
        },
        help="ส่วนงานที่จัดโครงการ อาจต่างจากส่วนงานเจ้าของงบประมาณ",
    )

    @api.depends("department_analytic_id")
    def _compute_organizer_department_id(self):
        """Default to the budget's ส่วนงาน; never overwrite a chosen value."""
        for rec in self:
            rec.organizer_department_id = (
                rec.organizer_department_id or rec.department_analytic_id
            )
