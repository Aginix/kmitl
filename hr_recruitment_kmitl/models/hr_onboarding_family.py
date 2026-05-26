from odoo import fields, models


class HrOnboardingFamily(models.Model):
    _name = "hr.onboarding.family"
    _description = "HR Onboarding Family Member"
    _inherit = ["hr.applicant.tracked.child"]

    onboarding_id = fields.Many2one(
        "hr.onboarding",
        required=True,
        ondelete="cascade",
        index=True,
    )
    relation_id = fields.Many2one(
        "hr.employee.relative.relation", required=True, tracking=True
    )
    identification_id = fields.Char(tracking=True)
    prefix_id = fields.Many2one("hr.employee.prefix", tracking=True)
    first_name = fields.Char(tracking=True)
    middle_name = fields.Char(tracking=True)
    last_name = fields.Char(tracking=True)
    date_of_birth = fields.Date(tracking=True)
    job = fields.Char(tracking=True)
    phone = fields.Char(tracking=True)
    status = fields.Selection(
        [("alive", "Alive"), ("pass_away", "Pass Away"), ("divorce", "Divorce")],
        tracking=True,
    )

    def _applicant_for_tracking(self):
        self.ensure_one()
        return self.onboarding_id.applicant_id

    def _tracking_label(self):
        self.ensure_one()
        relation = self.relation_id.name or ""
        name_parts = [p for p in [self.first_name or "", self.last_name or ""] if p]
        name = " ".join(name_parts)
        parts = [p for p in [relation, name] if p]
        return " — ".join(parts) if parts else self._description
