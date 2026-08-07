from werkzeug.utils import redirect

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers import portal


class WorkAcceptance(portal.CustomerPortal):

    @http.route(['/wa/view/<int:wa_id>'], type='http', auth="public", website=True)
    def work_acceptance_view(self, wa_id, access_token=None, committee_token=None, message=False, **kw):
        try:
            wa_sudo = self._document_check_access('work.acceptance', wa_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        committee = request.env['work.acceptance.committee'].sudo().search([
            ('access_token', '=', committee_token),
            ], limit=1)

        values = {
            'work_acceptance': wa_sudo,
            'message': message,
            'report_type': 'html',
        }

        if committee:
            values['wa_committee'] = committee

        values = self._get_page_view_values(wa_sudo, access_token, values, False, False)

        return request.render("purchase_work_acceptance_portal.work_acceptance_portal_template", values)

    @http.route(['/wa/view/<int:wa_id>/accept'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def work_acceptance_committee_confirm(self, wa_id, committee_token=None, access_token=None, **post):
        try:
            work_acceptance = self._document_check_access('work.acceptance', wa_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        committee = request.env['work.acceptance.committee'].sudo().search([
            ('access_token', '=', committee_token),
            ], limit=1)

        committee_user = committee.employee_id.user_id
        if not committee_user:
            return request.not_found()

        comment_text = "อนุมัติ"

        pending_reviews = work_acceptance.review_ids.filtered(
            lambda review: review.status == "pending" and (committee_user in review.reviewer_ids)
        )

        if pending_reviews:
            pending_reviews.write({"comment": comment_text})
            work_acceptance.with_user(committee_user).with_context(
                **committee_user.context_get()
            )._validate_tier(pending_reviews)
            work_acceptance._update_counter({"review_deleted": True})

        return redirect(f"/wa/view/{work_acceptance.id}?access_token={work_acceptance.access_token}&committee_token={committee.access_token}")

    @http.route(['/wa/view/<int:wa_id>/reject'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def work_acceptance_committee_reject(self, wa_id, committee_token=None, access_token=None, **post):
        try:
            work_acceptance = self._document_check_access('work.acceptance', wa_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        committee = request.env['work.acceptance.committee'].sudo().search([
            ('access_token', '=', committee_token),
            ], limit=1)

        committee_user = committee.employee_id.user_id
        if not committee_user:
            return request.not_found()

        comment_text = post.get("comment") or "อนุมัติ"

        pending_reviews = work_acceptance.review_ids.filtered(
            lambda review: review.status == "pending" and (committee_user in review.reviewer_ids)
        )

        if pending_reviews:
            pending_reviews.write({"comment": comment_text})
            work_acceptance.with_user(committee_user).with_context(
                **committee_user.context_get()
            )._validate_tier(pending_reviews)
            work_acceptance._update_counter({"review_deleted": True})
            committee.write({"status": "other", "note": comment_text})

        return redirect(f"/wa/view/{work_acceptance.id}?access_token={work_acceptance.access_token}&committee_token={committee.access_token}")

