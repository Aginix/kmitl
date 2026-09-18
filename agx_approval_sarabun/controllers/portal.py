# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, request
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
                    [("owner_id.user_id", "=", request.env.user.id)]
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

        domain = [("owner_id.user_id", "=", request.env.user.id)]

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
            return self._render_approval_official_document(
                approval_request_sudo, report_type, download=download
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
        self, request_id, report_type, access_token=None, download=False, **kw
    ):
        """Render the approval request's official document in HTML or PDF."""
        try:
            approval_request_sudo = self._document_check_access(
                "approval.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        return self._render_approval_official_document(
            approval_request_sudo, report_type, download=download
        )

    def _render_approval_official_document(
        self, approval_request_sudo, report_type, download=False
    ):
        """Serve the approval request's active หนังสือ — the official document
        (ADR-0015): the Sarabun document rendered through สารบรรณ's own layout, not
        a standalone approval report. No active หนังสือ yet (draft / to_send) →
        back to the record page, matching "no document before submit".

        Rendered sudo: a portal magic-link visitor has read on the request via the
        access token but not on the sarabun.document; the official PDF is a system
        render gated by the request's own access, already checked above."""
        document = approval_request_sudo.active_sarabun_document_id.sudo()
        if not document:
            return request.redirect(approval_request_sudo.access_url or "/my")

        if report_type == "pdf":
            pdf = document._get_official_pdf()
            filename = (document._get_report_base_filename() or "sarabun") + ".pdf"
            disposition = content_disposition(
                filename, "attachment" if download else "inline"
            )
            return request.make_response(
                pdf,
                headers=[
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", len(pdf)),
                    ("Content-Disposition", disposition),
                ],
            )

        # html / text: the A4-framed on-screen preview
        html = document._render_preview_html()
        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", len(html)),
            ],
        )
