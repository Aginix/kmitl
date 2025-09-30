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

        committee_user = committee.employee_id.user_id
        if not committee_user:
            return request.not_found()

        work_acceptance = request.env(user=committee_user.id)['work.acceptance'].browse(committee.wa_id.id)

        comment_text = post.get("comment") or "อนุมัติ"

        pending_reviews = work_acceptance.review_ids.filtered(
            lambda review: review.status == "pending" and (committee_user in review.reviewer_ids)
        )

        if pending_reviews:
            pending_reviews.write({"comment": comment_text})
            work_acceptance.with_user(committee_user)._validate_tier(pending_reviews)
            work_acceptance._update_counter({"review_deleted": True})

        return request.render(
            "purchase_work_acceptance_portal.work_acceptance_portal_template",
            {
                'work_acceptance': committee.wa_id,
                'committee': committee,
            }
        )

    @http.route(['/wa/view/<int:committee_id>/reject'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def work_acceptance_committee_reject(self, committee_id=None, access_token=None, **post):
        committee = request.env['work.acceptance.committee'].sudo().browse(int(committee_id))
        if not committee.exists() or access_token != committee.access_token:
            return request.not_found()

        committee_user = committee.employee_id.user_id
        if not committee_user:
            return request.not_found()

        work_acceptance = request.env(user=committee_user.id)['work.acceptance'].browse(committee.wa_id.id)

        comment_text = post.get("comment") or "อนุมัติ"

        pending_reviews = work_acceptance.review_ids.filtered(
            lambda review: review.status == "pending" and (committee_user in review.reviewer_ids)
        )

        if pending_reviews:
            pending_reviews.write({"comment": comment_text})
            work_acceptance.with_user(committee_user)._validate_tier(pending_reviews)
            work_acceptance._update_counter({"review_deleted": True})
            committee.write({"status": "not_accept", "note": comment_text})

        return request.render(
            "purchase_work_acceptance_portal.work_acceptance_portal_template",
            {
                'work_acceptance': committee.wa_id,
                'committee': committee,
            }
        )

