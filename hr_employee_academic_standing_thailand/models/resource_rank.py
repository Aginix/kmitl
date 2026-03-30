import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResourceRank(models.Model):
    _name = "resource.rank"
    _description = "ResourceRank"

    name = fields.Char()
    name_abbreviation = fields.Char()
    name_en = fields.Char(string="Name English")
    name_abbreviation_en = fields.Char(string="Name Abbreviation English")
    rank_agency_id = fields.Many2one("resource.rank.agency", string="Rank Agency")
    sequence = fields.Integer()
