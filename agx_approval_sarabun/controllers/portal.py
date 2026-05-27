# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools.translate import _


class ApprovalRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add approval request count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if "approval_request_count" in counters:
            approval_request_count = (
                request.env["approval.request"].search_count(
                    [("owner_id", "=", request.env.user.id)]
                )
                if request.env["approval.request"].check_access_rights(
                    "read", raise_exception=False
                )
                else 0
            )
            values["approval_request_count"] = approval_request_count
        return values

    @http.route(
        ["/my/approval_requests", "/my/approval_requests/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_approval_requests(self, page=1, sortby=None, filterby=None, **kw):
        """Display approval requests in portal."""
        values = self._prepare_portal_layout_values()
        ApprovalRequest = request.env["approval.request"]

        domain = [("owner_id", "=", request.env.user.id)]

        # Sorting
        searchbar_sortings = {
            "date": {"label": _("Date"), "order": "create_date desc"},
            "name": {"label": _("Reference"), "order": "name"},
        }
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # Paging
        approval_request_count = ApprovalRequest.search_count(domain)
        pager = portal_pager(
            url="/my/approval_requests",
            total=approval_request_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )

        # Content
        approval_requests = ApprovalRequest.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values.update(
            {
                "approval_requests": approval_requests,
                "page_name": "approval_request",
                "pager": pager,
                "default_url": "/my/approval_requests",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render(
            "agx_approval_sarabun.portal_my_approval_requests", values
        )

    @http.route(
        ["/my/approval_request/<int:request_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_approval_request(
        self,
        request_id,
        report_type=None,
        access_token=None,
        message=False,
        download=False,
        **kw,
    ):
        """Display single approval request in portal."""
        try:
            approval_request_sudo = self._document_check_access(
                "approval.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=approval_request_sudo,
                report_type=report_type,
                report_ref="agx_approval.action_report_approval_request",
                download=download,
            )

        values = self._approval_request_get_page_view_values(
            approval_request_sudo, access_token, **kw
        )
        return request.render(
            "agx_approval_sarabun.portal_approval_request_page", values
        )

    def _approval_request_get_page_view_values(
        self, approval_request, access_token, **kwargs
    ):
        values = {
            "approval_request": approval_request,
            "page_name": "approval_request",
            "report_type": "html",
        }
        return self._get_page_view_values(
            approval_request,
            access_token,
            values,
            "my_approval_requests",
            False,
            **kwargs,
        )

    @http.route(
        ["/my/approval_request/<int:request_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_approval_request_report(
        self, request_id, report_type, access_token=None, **kw
    ):
        """Render approval request report in HTML or PDF format."""
        try:
            approval_request_sudo = self._document_check_access(
                "approval.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            report = request.env.ref(
                "agx_approval.action_report_approval_request"
            )
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [approval_request_sudo.id]
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            report = request.env.ref(
                "agx_approval.action_report_approval_request"
            )
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [approval_request_sudo.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Approval Request - {approval_request_sudo.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
