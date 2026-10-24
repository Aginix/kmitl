# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    student_code = fields.Char(
        string="Student ID",
        index=True,
        copy=False,
        tracking=True,
    )
    student_faculty = fields.Char(string="Faculty")
    student_curriculum = fields.Char(string="Curriculum")
    is_student = fields.Boolean(compute="_compute_is_student")

    _sql_constraints = [
        (
            "student_code_uniq",
            "unique(student_code)",
            "A student ID can belong to one contact only.",
        ),
    ]

    @api.depends("partner_type_id")
    def _compute_is_student(self):
        student_type = self.env.ref("partner_type_kmitl.partner_type_student")
        for partner in self:
            partner.is_student = partner.partner_type_id == student_type

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
    def _kmitl_student_match(self, student_code, vat=None):
        """The contact a student is already on: by student ID, else by national
        ID on a student contact without one (ADR 0001). Never creates."""
        partner = self.search([("student_code", "=", student_code)], limit=1)
        if not partner and vat:
            partner = self.search(
                [
                    ("vat", "=", vat),
                    (
                        "partner_type_id",
                        "=",
                        self.env.ref("partner_type_kmitl.partner_type_student").id,
                    ),
                    ("student_code", "=", False),
                ],
                limit=1,
            )
        return partner

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
