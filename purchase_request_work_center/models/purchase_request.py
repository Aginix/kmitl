from odoo import api, models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "work.center.mixin"]

    @api.model
    def _work_center_routing_fields(self):
        return super()._work_center_routing_fields() + ["requesting_department_id"]
