import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrEmployeeRankNobility(models.Model):
    _name = "hr.employee.rank.nobility"
    _description = "HrEmployeeRankNobility"

    name = fields.Char()
    name_abbreviation = fields.Char()
    name_en = fields.Char(string="Name English")
    name_abbreviation_en = fields.Char(string="Name Abbreviation English")
