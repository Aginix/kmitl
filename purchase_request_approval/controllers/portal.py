# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools.translate import _


class PurchaseRequestApprovalPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add purchase request approval count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if "purchase_request_approval_count" in counters:
            purchase_request_approval_count = (
                request.env["purchase.request.approval"].search_count([])
                if request.env["purchase.request.approval"].check_access_rights(
                    "read", raise_exception=False
                )
                else 0
            )
            values["purchase_request_approval_count"] = purchase_request_approval_count
        return values

    @http.route(
        ["/my/purchase_request_approvals", "/my/purchase_request_approvals/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_purchase_request_approvals(self, page=1, sortby=None, filterby=None, **kw):
        """Display purchase request approvals in portal."""
        values = self._prepare_portal_layout_values()
        PurchaseRequestApproval = request.env["purchase.request.approval"]

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
        purchase_request_approval_count = PurchaseRequestApproval.search_count(domain)
        pager = portal_pager(
            url="/my/purchase_request_approvals",
            total=purchase_request_approval_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )

        # Content
        purchase_request_approvals = PurchaseRequestApproval.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values.update(
            {
                "purchase_request_approvals": purchase_request_approvals,
                "page_name": "purchase_request_approval",
                "pager": pager,
                "default_url": "/my/purchase_request_approvals",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("purchase_request_approval.portal_my_purchase_request_approvals", values)

    @http.route(
        ["/my/purchase_request_approval/<int:request_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_purchase_request_approval(self, request_id, report_type=None, access_token=None, message=False, download=False, **kw):
        """Display single purchase request approval in portal."""
        try:
            purchase_request_approval_sudo = self._document_check_access(
                "purchase.request.approval", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=purchase_request_approval_sudo, report_type=report_type, report_ref='purchase_request_approval.action_report_purchase_request_approvals', download=download)

        values = self._purchase_request_approval_get_page_view_values(purchase_request_approval_sudo, access_token, **kw)
        return request.render("purchase_request_approval.portal_purchase_request_approval_page", values)

    def _purchase_request_approval_get_page_view_values(self, purchase_request_approval, access_token, **kwargs):
        values = {
            "purchase_request_approval": purchase_request_approval,
            "page_name": "purchase_request_approval",
            "report_type": "html",
        }
        return self._get_page_view_values(purchase_request_approval, access_token, values, 'my_purchase_request_approvals', False, **kwargs)

    @http.route(
        ["/my/purchase_request_approval/<int:request_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_purchase_request_approval_report(
        self, request_id, report_type, access_token=None, **kw
    ):
        """Render purchase request approval report in HTML or PDF format."""
        try:
            purchase_request_approval_sudo = self._document_check_access(
                "purchase.request.approval", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            # Render HTML report directly
            report = request.env.ref("purchase_request_approval.report_purchase_request_approval")
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [purchase_request_approval_sudo.id]
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
            report = request.env.ref("purchase_request_approval.report_purchase_request_approval")
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [purchase_request_approval_sudo.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Purchase Request - {purchase_request_approval_sudo.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
