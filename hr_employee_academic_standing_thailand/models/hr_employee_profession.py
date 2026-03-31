import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrEmployeeProfession(models.Model):
    _name = "hr.employee.profession"
    _description = "HrEmployeeProfession"

    name = fields.Char()
    name_abbreviation = fields.Char()
    name_en = fields.Char(string="Name English")
    name_abbreviation_en = fields.Char(string="Name Abbreviation English")
