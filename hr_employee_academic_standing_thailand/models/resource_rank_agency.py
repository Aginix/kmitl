from odoo import fields, models


class ResourceRankAgency(models.Model):
    _name = "resource.rank.agency"
    _description = "ResourceRankAgency"

    name = fields.Char(translate=True)
    name_abbreviation = fields.Char(translate=True)
