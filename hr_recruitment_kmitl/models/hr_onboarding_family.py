from odoo import fields, models


class HrOnboardingFamily(models.Model):
    _name = "hr.onboarding.family"
    _description = "HR Onboarding Family Member"

    onboarding_id = fields.Many2one(
        "hr.onboarding",
        required=True,
        ondelete="cascade",
        index=True,
    )
    relation_id = fields.Many2one("hr.employee.relative.relation", required=True)
    identification_id = fields.Char()
    prefix_id = fields.Many2one("hr.employee.prefix")
    first_name = fields.Char()
    middle_name = fields.Char()
    last_name = fields.Char()
    date_of_birth = fields.Date()
    job = fields.Char()
    phone = fields.Char()
    status = fields.Selection(
        [("alive", "Alive"), ("pass_away", "Pass Away"), ("divorce", "Divorce")]
    )
