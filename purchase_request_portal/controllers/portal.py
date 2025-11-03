# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools.translate import _


class PurchaseRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add purchase request count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if "purchase_request_count" in counters:
            purchase_request_count = (
                request.env["purchase.request"].search_count([])
                if request.env["purchase.request"].check_access_rights(
                    "read", raise_exception=False
                )
                else 0
            )
            values["purchase_request_count"] = purchase_request_count
        return values

    @http.route(
        ["/my/purchase_requests", "/my/purchase_requests/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_purchase_requests(self, page=1, sortby=None, filterby=None, **kw):
        """Display purchase requests in portal."""
        values = self._prepare_portal_layout_values()
        PurchaseRequest = request.env["purchase.request"]

        domain = []

        # Sorting
        searchbar_sortings = {
            "date": {"label": _("Date"), "order": "create_date desc"},
            "name": {"label": _("Reference"), "order": "name"},
        }
        if not sortby:
            sortby = "date"
        order = searchbar_sortings[sortby]["order"]

        # Paging
        purchase_request_count = PurchaseRequest.search_count(domain)
        pager = portal_pager(
            url="/my/purchase_requests",
            total=purchase_request_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )

        # Content
        purchase_requests = PurchaseRequest.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values.update(
            {
                "purchase_requests": purchase_requests,
                "page_name": "purchase_request",
                "pager": pager,
                "default_url": "/my/purchase_requests",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("purchase_request_portal.portal_my_purchase_requests", values)

    @http.route(
        ["/my/purchase_request/<int:request_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_purchase_request(self, request_id, report_type=None, access_token=None, message=False, download=False, **kw):
        """Display single purchase request in portal."""
        try:
            purchase_request_sudo = self._document_check_access(
                "purchase.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=purchase_request_sudo, report_type=report_type, report_ref='purchase_request.action_report_purchase_requests', download=download)

        values = {
            "purchase_request": purchase_request_sudo,
            "page_name": "purchase_request",
            "report_type": "html",
        }
        return request.render("purchase_request_portal.portal_purchase_request_page", values)

    @http.route(
        ["/my/purchase_request/<int:request_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_purchase_request_report(
        self, request_id, report_type, access_token=None, **kw
    ):
        """Render purchase request report in HTML or PDF format."""
        try:
            purchase_request_sudo = self._document_check_access(
                "purchase.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            # Render HTML report directly
            report = request.env.ref("purchase_request.report_purchase_request")
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [purchase_request_sudo.id]
            )[0]
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            # Render PDF report
            report = request.env.ref("purchase_request.report_purchase_request")
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [purchase_request_sudo.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Purchase Request - {purchase_request_sudo.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
