# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    @api.model
    def _get_tier_validation_model_names(self):
        """Allow tier definitions to target disbursement requests."""
        res = super()._get_tier_validation_model_names()
        res.append("disbursement.request")
        return res
