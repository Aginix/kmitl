from odoo import api, http
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

    @http.route(['/wa/view/<int:committee_id>/accept'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def work_acceptance_committee_confirm(self, committee_id=None, access_token=None, **post):
        committee = request.env['work.acceptance.committee'].sudo().browse(int(committee_id))
        if not committee.exists() or access_token != committee.access_token:
            return request.not_found()
        user = committee.employee_id.user_id.id
        user2 = committee.employee_id.user_id
        if not user:
            return request.not_found()
        env = request.env(user=user)
        wa_id = committee.wa_id.id
        wa = env['work.acceptance'].browse(wa_id)
        comment = post.get("comment") or "อนุมัติ"
        reviews = wa.review_ids.filtered(
            lambda r: r.status == "pending" and (user2 in r.reviewer_ids)
        )
        if reviews:
            reviews.write({"comment": comment})
            wa.with_user(user2)._validate_tier(reviews)
            wa._update_counter({"review_deleted": True})
        ctx = {
            "active_id": wa.id,
            "active_model": "work.acceptance",
            "validate_as_not_accept": False,
            "comment": "ทดสอบๆ"
        }

        # wa.with_context(**ctx).validate_tier()

        # wa.with_user(user).with_context(**ctx).validate_tier()


        return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", {
            'work_acceptance': committee.wa_id,
            'committee': committee,
        })

    @http.route(['/wa/view/reject'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def work_acceptance_committee_reject(self, committee_id=None, access_token=None, **post):
        committee = request.env['work.acceptance.committee'].sudo().browse(int(committee_id))
        if not committee.exists() or access_token != committee.access_token:
            return request.not_found()

        wa = committee.wa_id
        user = committee.employee_id.user_id
        if not user:
            return request.not_found()


        ctx = {
            "active_id": wa.id,
            "active_model": "work.acceptance",
            "validate_as_not_accept": True,
            "default_comment": post.get('comment', 'ไม่รับเพราะ...'),
        }

        wa.with_user(user).with_context(**ctx).validate_tier()

        return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", {
            'work_acceptance': wa,
            'committee': committee,
        })

        # <button
        #                     name="validate_tier"
        #                     string="Not Accept"
        #                     attrs="{'invisible': [('can_review', '=', False)]}"
        #                     type="object"
        #                     class="btn-icon btn-danger"
        #                     icon="fa-thumbs-down"
        #                     context="{'validate_as_not_accept': True, 'default_comment': 'ไม่รับเพราะ...'}"
        #                 />

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
