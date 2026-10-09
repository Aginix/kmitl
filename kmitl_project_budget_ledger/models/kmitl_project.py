from odoo import models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _auto_resync_commitment(self):
        """Superseded by the ledger's automatic top-up/release on transfer
        (budget ADR-0016, Q5): money moved onto or off the project's
        coordinate after it reserved now moves the reservation with it, even
        once spending has started."""
        return None
