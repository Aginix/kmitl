# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _kmitl_student_vals(self, row):
        """Contact values for a student catalog row: the Thai name with its
        prefix (นายสมชาย ใจดี), faculty and curriculum."""
        name = "%s%s %s" % (
            row.get("prename_th") or "",
            row.get("first_name_th") or "",
            row.get("last_name_th") or "",
        )
        return {
            "name": name.strip(),
            "student_faculty": row.get("faculty_name_th") or False,
            "student_curriculum": row.get("curriculum_name_th") or False,
        }

    @api.model
    def _kmitl_student_lookup(self, student_codes):
        found = super()._kmitl_student_lookup(student_codes)
        rows = self.env["kmitl.student.catalog"].fetch(
            [code for code in student_codes if code not in found]
        )
        found.update(
            {code: self._kmitl_student_vals(row) for code, row in rows.items()}
        )
        return found

    def action_refresh_from_kmitl(self):
        """Re-read name, faculty and curriculum from the student catalog."""
        students = self.filtered("student_code")
        rows = self.env["kmitl.student.catalog"].fetch(students.mapped("student_code"))
        missing = students.filtered(lambda p: p.student_code not in rows)
        if missing:
            raise UserError(
                _("Not found in the KMITL student catalog: %s")
                % ", ".join(missing.mapped("student_code"))
            )
        for partner in students:
            partner.write(self._kmitl_student_vals(rows[partner.student_code]))
        return True
