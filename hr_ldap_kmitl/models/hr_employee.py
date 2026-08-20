from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.constrains("work_email")
    def _check_kmitl_unique_work_email(self):
        """Work email is the key used to link an employee to its user account,
        so it must be unique. Enforced going forward only (existing duplicates
        are not retroactively blocked, keeping install/upgrade safe); blank
        emails are ignored.
        """
        for employee in self:
            email = (employee.work_email or "").strip().lower()
            if not email:
                continue
            candidates = self.sudo().search(
                [
                    ("id", "!=", employee.id),
                    ("work_email", "=ilike", email),
                ],
                limit=10,
            )
            if candidates.filtered(
                lambda e: (e.work_email or "").strip().lower() == email
            ):
                raise ValidationError(
                    _(
                        "Work email '%s' is already used by another employee.\n"
                        "Work email must be unique because it is the key used "
                        "to link an employee to their user account."
                    )
                    % employee.work_email
                )
