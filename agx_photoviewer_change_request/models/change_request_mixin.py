from odoo import models


class ChangeRequestMixin(models.AbstractModel):
    _inherit = "change.request.mixin"

    def unlink(self):
        # The record's files go with it: their requests need no cancelling.
        return super(
            ChangeRequestMixin, self.with_context(change_request_record_unlink=True)
        ).unlink()
