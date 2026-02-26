# -*- coding: utf-8 -*-
from odoo import fields, models


class HrPreboardingEducation(models.Model):
    _name = "hr.preboarding.education"
    _description = "Preboarding Education History"

    preboarding_id = fields.Many2one(
        "hr.preboarding", required=True, ondelete="cascade"
    )
    degree = fields.Char("Degree")
    institution = fields.Char("Institution")
    field_of_study = fields.Char("Field of Study")
    graduation_year = fields.Char("Graduation Year")
    gpa = fields.Float("GPA")
