# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request


class HrRecruitmentPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "application_count" in counters:
            domain = self._get_applications_domain()
            values["application_count"] = (
                request.env["hr.applicant"].sudo().search_count(domain)
            )
        return values

    def _get_applications_domain(self):
        partner = request.env.user.partner_id
        return [
            "|",
            ("partner_id", "=", partner.id),
            ("email_from", "=ilike", partner.email or ""),
            ("active", "in", [True, False]),
        ]

    @http.route(
        ["/my/applications", "/my/applications/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_applications(self, page=1, sortby=None, **kw):
        HrApplicant = request.env["hr.applicant"].sudo()
        domain = self._get_applications_domain()

        sortings = {
            "date": {"label": "Date Applied", "order": "create_date desc"},
            "name": {"label": "Job Position", "order": "job_id asc, name asc"},
            "stage": {"label": "Stage", "order": "stage_id asc"},
        }
        if not sortby or sortby not in sortings:
            sortby = "date"
        order = sortings[sortby]["order"]

        application_count = HrApplicant.search_count(domain)
        pager = portal_pager(
            url="/my/applications",
            url_args={"sortby": sortby},
            total=application_count,
            page=page,
            step=self._items_per_page,
        )
        applications = HrApplicant.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = {
            "applications": applications,
            "page_name": "application",
            "pager": pager,
            "default_url": "/my/applications",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render("hr_recruitment_kmitl.portal_my_applications", values)

    @http.route(
        ["/my/application/<int:application_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_application(self, application_id, **kw):
        partner = request.env.user.partner_id
        application = (
            request.env["hr.applicant"]
            .sudo()
            .with_context(active_test=False)
            .browse(application_id)
        )

        if not application.exists():
            return request.redirect("/my")

        # Ownership check
        partner_match = (
            application.partner_id and application.partner_id.id == partner.id
        )
        email_match = (
            application.email_from
            and partner.email
            and application.email_from.lower() == partner.email.lower()
        )
        if not partner_match and not email_match:
            return request.redirect("/my")

        # Fetch stages relevant to this job for the progress bar
        stage_domain = [
            "|",
            ("job_ids", "=", False),
            ("job_ids", "in", application.job_id.ids if application.job_id else []),
        ]
        all_stages = (
            request.env["hr.recruitment.stage"]
            .sudo()
            .search(stage_domain, order="sequence asc")
        )

        values = {
            "application": application,
            "all_stages": all_stages,
            "page_name": "application",
        }
        return request.render("hr_recruitment_kmitl.portal_application_detail", values)
