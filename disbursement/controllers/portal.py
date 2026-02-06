# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class DisbursementPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        """Add disbursement request count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        if "disbursement_request_count" in counters:
            DisbursementRequest = request.env["disbursement.request"]
            values["disbursement_request_count"] = (
                DisbursementRequest.search_count([])
                if DisbursementRequest.check_access_rights("read", raise_exception=False)
                else 0
            )
        return values

    @http.route(
        ["/my/disbursements", "/my/disbursements/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_disbursement_requests(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        """Display list of disbursement requests"""
        DisbursementRequest = request.env["disbursement.request"]

        # Sorting options
        sortings = {
            "date": {"label": "Date", "order": "date desc"},
            "name": {"label": "Reference", "order": "name"},
        }

        # Default sort
        if not sortby:
            sortby = "date"
        order = sortings[sortby]["order"]

        # Count total requests
        domain = []
        request_count = DisbursementRequest.search_count(domain)

        # Pagination
        pager = portal_pager(
            url="/my/disbursements",
            url_args={"sortby": sortby},
            total=request_count,
            page=page,
            step=self._items_per_page,
        )

        # Fetch requests
        requests = DisbursementRequest.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values = {
            "date": date_begin,
            "requests": requests,
            "page_name": "disbursement_request",
            "pager": pager,
            "default_url": "/my/disbursements",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render(
            "disbursement.portal_my_disbursement_requests", values
        )

    @http.route(
        ["/my/disbursement/<int:request_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_disbursement_request(self, report_type=None, download=False, request_id=None, access_token=None, **kw):
        """Display single disbursement request detail"""
        try:
            disbursement_request_sudo = self._document_check_access(
                "disbursement.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=disbursement_request_sudo, report_type=report_type, report_ref='disbursement.action_report_disbursement_request', download=download)

        values = self._disbursement_request_get_page_view_values(
            disbursement_request_sudo, access_token, **kw
        )
        return request.render(
            "disbursement.portal_disbursement_request_page", values
        )

    def _disbursement_request_get_page_view_values(
        self, disbursement_request, access_token, **kwargs
    ):
        """Prepare values for disbursement request detail page"""
        values = {
            "disbursement_request": disbursement_request,
            "object": disbursement_request,
            "token": access_token,
            "report_type": "html",
        }
        return self._get_page_view_values(
            disbursement_request,
            access_token,
            values,
            "my_disbursements_history",
            False,
            **kwargs
        )

    @http.route(
        ["/my/disbursement/<int:request_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_disbursement_request_report(
        self,
        request_id=None,
        access_token=None,
        report_type="html",
        download=False,
        **kw
    ):
        """Render HTML or PDF report"""
        try:
            disbursement_request_sudo = self._document_check_access(
                "disbursement.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            # Render HTML report directly from template
            html = request.env["ir.qweb"]._render(
                "disbursement.report_disbursement_request",
                {"docs": disbursement_request_sudo},
            )
            return request.make_response(html)

        elif report_type == "pdf":
            # Generate PDF
            report = request.env.ref(
                "disbursement.action_report_disbursement_request"
            )
            pdf, _ = report._render_qweb_pdf(disbursement_request_sudo.ids)

            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
            ]

            if download:
                pdfhttpheaders.append(
                    (
                        "Content-Disposition",
                        f"attachment; filename={disbursement_request_sudo._get_report_base_filename()}.pdf;",
                    )
                )

            return request.make_response(pdf, headers=pdfhttpheaders)
