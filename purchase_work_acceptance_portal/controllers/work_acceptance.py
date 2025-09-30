from werkzeug.utils import redirect

from odoo import api, http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError

from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class WorkAcceptance(portal.CustomerPortal):

    @http.route(['/wa/view/<int:committee_id>'], type='http', auth="public", website=True)
    def work_acceptance_committee_portal(self, committee_id, access_token=None, message=False, **kw):
        try:
            wa_committee_sudo = self._document_check_access('work.acceptance.committee', committee_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'committee': wa_committee_sudo,
            'work_acceptance': wa_committee_sudo.wa_id,
            'message': message,
            'report_type': 'html',
        }

        values = self._get_page_view_values(wa_committee_sudo, access_token, values, False, False)

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

        comment_text = "อนุมัติ"

        pending_reviews = work_acceptance.review_ids.filtered(
            lambda review: review.status == "pending" and (committee_user in review.reviewer_ids)
        )

        if pending_reviews:
            pending_reviews.write({"comment": comment_text})
            work_acceptance.with_user(committee_user)._validate_tier(pending_reviews)
            work_acceptance._update_counter({"review_deleted": True})

        return redirect(f"/wa/view/{committee.id}?access_token={committee.access_token}")

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

        return redirect(f"/wa/view/{committee.id}?access_token={committee.access_token}")

