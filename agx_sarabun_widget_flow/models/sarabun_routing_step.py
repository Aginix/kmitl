from odoo import api, models


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    @api.onchange("document_id")
    def _onchange_document_default_order(self):
        """Keep an explicit ``default_order``: the flow widget's per-Layer "+"
        passes that Layer's Stage, which the base auto-increment would otherwise
        overwrite with a new last Stage. Save & New strips ``default_*``, so the
        following steps still auto-increment."""
        if "default_order" in self.env.context:
            return
        return super()._onchange_document_default_order()
