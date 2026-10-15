from odoo import api, models

WORK_CENTER_FIELDS = ["work_center_id", "work_center_manual"]


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "work.center.mixin"]

    @api.model
    def _work_center_routing_fields(self):
        return super()._work_center_routing_fields() + ["requesting_department_id"]

    # The work center stays editable while the พจ.1 is under or after tier
    # validation (ADR-0001: it can be changed by hand in every state).
    @api.model
    def _get_under_validation_exceptions(self):
        return super()._get_under_validation_exceptions() + WORK_CENTER_FIELDS

    @api.model
    def _get_after_validation_exceptions(self):
        return super()._get_after_validation_exceptions() + WORK_CENTER_FIELDS
