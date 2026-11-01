from odoo import models


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def _check_route_edit_route(self):
        """A route edit (e.g. re-targeting a waiting บุคลากร step) can leave a capacity
        the new person does not hold — refuse it at save, as ``action_send`` does,
        rather than when the signer acts."""
        super()._check_route_edit_route()
        self.routing_step_ids.filtered(
            lambda s: s.state in ("waiting", "active")
        )._check_person_capacity()
