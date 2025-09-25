from odoo import http
from odoo.http import request


class WorkAccpetance(http.Controller):
    @http.route(['/purchase/portal/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_form(self, order_id, **kw):
        purchase = request.env['purchase.order'].sudo().browse(order_id)

        if not purchase.exists():
            return request.not_found()

        values = {
            'purchase': purchase,
        }
        return request.render("purchase_work_accpetance_portal.portal_my_purchase", values)
