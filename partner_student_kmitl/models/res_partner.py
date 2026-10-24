# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


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
    def _kmitl_student_lookup(self, student_codes):
        """``{student_code: contact values}`` (name, faculty, curriculum) for
        students no contact carries yet; an unknown code is absent. Finds
        nothing here — ``partner_student_kmitl_api`` reads the KMITL student
        catalog."""
        return {}

    @api.model
    def _kmitl_student_match(self, vat_by_code):
        """``{student_code: contact}`` for the students already on a contact:
        by student ID, else by national ID on a student contact without one
        (ADR 0001). Two searches however many codes; never creates."""
        found = {
            partner.student_code: partner
            for partner in self.search([("student_code", "in", list(vat_by_code))])
        }
        code_by_vat = {
            vat: code for code, vat in vat_by_code.items() if vat and code not in found
        }
        if code_by_vat:
            student_type = self.env.ref("partner_type_kmitl.partner_type_student")
            for partner in self.search(
                [
                    ("vat", "in", list(code_by_vat)),
                    ("partner_type_id", "=", student_type.id),
                    ("student_code", "=", False),
                ]
            ):
                found.setdefault(code_by_vat[partner.vat], partner)
        return found
