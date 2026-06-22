from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrJob(models.Model):
    _inherit = "hr.job"

    @api.model
    def _cron_close_expired_jobs(self):
        expired = self.search(
            [
                ("date_close", "<=", fields.Datetime.now()),
                ("date_close", "!=", False),
                ("website_published", "=", True),
            ]
        )
        expired.write({"website_published": False})

    role = fields.Selection(
        [("academic", "Academic"), ("support", "Support")],
    )
    education_level_ids = fields.Many2many(
        "hr.recruitment.degree",
        string="Education Levels",
    )
    category_ids = fields.Many2many(
        "hr.job.category",
        string="Tags",
    )
    salary_min = fields.Monetary(string="Minimum Salary", currency_field="currency_id")
    salary_max = fields.Monetary(string="Maximum Salary", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.ref("base.THB"),
    )
    date_close = fields.Datetime(string="Closing Date")
    start_service_date = fields.Date()
    exam_eligible_announce_date = fields.Date(
        string="Eligible Candidates Announcement Date"
    )
    exam_passed_announce_date = fields.Date(
        string="Passed Candidates Announcement Date"
    )
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    old_code = fields.Char(string="Position Code")
    kmitl_employee_type = fields.Selection(
        selection=[
            ("B", "พนักงานสถาบันเงินงบประมาณ"),
            ("N", "พนักงานสถาบันเงินรายได้"),
            ("E", "พนักงานสถาบันประเภทพิเศษ"),
        ],
        string="Employee Type",
    )

    @api.model_create_multi
    def create(self, vals):
        record = super().create(vals)
        record._make_attachments_public(vals)
        return record

    def write(self, vals):
        res = super().write(vals)
        self._make_attachments_public(vals)
        if vals.get("website_published") or "date_close" in vals:
            self._check_date_close_on_publish()
        return res

    def _check_date_close_on_publish(self):
        now = fields.Datetime.now()
        for record in self:
            if not record.website_published:
                continue
            if not record.date_close or record.date_close <= now:
                raise ValidationError(
                    _(
                        "Cannot publish '%(name)s': closing date must be in the future.",
                        name=record.name,
                    )
                )

    @api.constrains("salary_min", "salary_max")
    def _check_range(self):
        for record in self:
            if record.salary_min > record.salary_max:
                raise ValidationError(_("Min salary cannot exceed max salary"))

    def _make_attachments_public(self, vals):
        if "attachment_ids" in vals:
            for record in self:
                record.attachment_ids.write({"public": True})


class HrJobCategory(models.Model):
    _name = "hr.job.category"
    _description = "Job Category"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
