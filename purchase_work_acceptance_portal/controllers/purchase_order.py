from odoo import http
from odoo.http import request


class PurchaseOrder(http.Controller):
    @http.route(['/purchase/view/<int:order_id>'],
                type='http', auth="public", website=True)
    def portal_my_purchase_form(self, order_id, access_token=None, committee_id=None, **kw):
        purchase = request.env['purchase.order'].sudo().browse(order_id)
        committee = request.env['work.acceptance.committee'].sudo().browse(int(committee_id))
        if not purchase.exists():
            return request.not_found()

        if not access_token or access_token != purchase.access_token:
            return request.not_found()

        values = {
            'purchase': purchase,
            'committee': committee
        }
        return request.render("purchase_work_acceptance_portal.purchase_portal_template", values)
