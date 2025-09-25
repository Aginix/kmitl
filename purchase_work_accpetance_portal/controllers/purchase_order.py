from odoo import http
from odoo.http import request


class PurchaseOrder(http.Controller):
    @http.route(['/purchase/portal/<int:order_id>/<string:access_token>'],
                type='http', auth="public", website=True)
    def portal_my_purchase_form(self, order_id, access_token=None, **kw):
        purchase = request.env['purchase.order'].sudo().browse(order_id)

        if not purchase.exists():
            return request.not_found()

        if not access_token or access_token != purchase.access_token:
            return request.not_found()

        values = {
            'purchase': purchase,
        }
        return request.render("purchase_work_accpetance_portal.purchase_portal_template", values)
