from odoo import models


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def action_send(self):
        """Validate person-mode capacities once the route is final (template seeded
        inside super) — the composer can still fix them; the signer mid-circulation
        can't. A raise rolls the whole send back (the number is assigned later)."""
        res = super().action_send()
        self.routing_step_ids.filtered(
            lambda s: s.state in ("waiting", "active")
        )._check_person_capacity()
        return res
