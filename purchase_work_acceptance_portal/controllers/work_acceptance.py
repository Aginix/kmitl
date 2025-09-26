from odoo import http
from odoo.http import request


class WorkAcceptance(http.Controller):
    @http.route(['/wa/test/<int:wa_id>'],
                type='http', auth="public", website=True)
    def work_acceptance_portal(self, wa_id,access_token=None, **kw):
        work_acceptance = request.env['work.acceptance'].sudo().browse(wa_id)

        if not work_acceptance.exists():
            return request.not_found()

        if not access_token or access_token != work_acceptance.access_token:
            return request.not_found()

        values = {
            'work_acceptance': work_acceptance,
        }
        return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", values)

    @http.route(['/wa/view/<int:committee_id>'], type='http', auth="public", website=True)
    def work_acceptance_committee_portal(self, committee_id, access_token=None, **kw):
        committee = request.env['work.acceptance.committee'].sudo().browse(committee_id)
        wa = request.env['work.acceptance'].sudo().browse(committee.wa_id.id)
        if not committee.exists():
            return request.not_found()

        if not access_token or access_token != committee.access_token:
            return request.not_found()

        values = {
            'committee': committee,
            'work_acceptance': wa,
        }
        return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", values)

    # @http.route(['/wa/portal/<int:wa_id>'],
    #             type='http', auth="public", website=True)
    # def work_acceptance_portal_all(self, wa_id, **kw):
    #     work_acceptance = request.env['work.acceptance'].sudo().browse(wa_id)

    #     if not work_acceptance.exists():
    #         return request.not_found()

    #     values = {
    #         'work_acceptance': work_acceptance,
    #     }
    #     return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", values)
