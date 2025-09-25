from odoo import http
from odoo.http import request


class WorkAcceptance(http.Controller):
    @http.route(['/wa/portal/<int:wa_id>/<string:access_token>'],
                type='http', auth="public", website=True)
    def work_acceptance_portal(self, wa_id, access_token=None, **kw):
        work_acceptance = request.env['work.acceptance'].sudo().browse(wa_id)

        if not work_acceptance.exists():
            return request.not_found()

        if not access_token or access_token != work_acceptance.access_token:
            return request.not_found()

        values = {
            'work_acceptance': work_acceptance,
        }
        return request.render("purchase_work_accpetance_portal.work_acceptance_portal_template", values)

    # @http.route(['/wa/portal/<int:wa_id>'],
    #             type='http', auth="public", website=True)
    # def work_acceptance_portal_all(self, wa_id, **kw):
    #     work_acceptance = request.env['work.acceptance'].sudo().browse(wa_id)

    #     if not work_acceptance.exists():
    #         return request.not_found()

    #     values = {
    #         'work_acceptance': work_acceptance,
    #     }
    #     return request.render("purchase_work_accpetance_portal.work_acceptance_portal_template", values)
