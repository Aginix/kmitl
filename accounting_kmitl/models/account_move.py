from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["posted"]
    _tier_validation_manual_config = False