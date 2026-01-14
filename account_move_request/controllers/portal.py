# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class AccountMoveRequestPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        """Add account move request count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        if "account_move_request_count" in counters:
            AccountMoveRequest = request.env["account.move.request"]
            values["account_move_request_count"] = (
                AccountMoveRequest.search_count([])
                if AccountMoveRequest.check_access_rights("read", raise_exception=False)
                else 0
            )
        return values

    @http.route(
        ["/my/account_move_requests", "/my/account_move_requests/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_account_move_requests(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        """Display list of account move requests"""
        AccountMoveRequest = request.env["account.move.request"]

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
        request_count = AccountMoveRequest.search_count(domain)

        # Pagination
        pager = portal_pager(
            url="/my/account_move_requests",
            url_args={"sortby": sortby},
            total=request_count,
            page=page,
            step=self._items_per_page,
        )

        # Fetch requests
        requests = AccountMoveRequest.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values = {
            "date": date_begin,
            "requests": requests,
            "page_name": "account_move_request",
            "pager": pager,
            "default_url": "/my/account_move_requests",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render(
            "account_move_request.portal_my_account_move_requests", values
        )

    @http.route(
        ["/my/account_move_request/<int:request_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_account_move_request(self, request_id=None, access_token=None, **kw):
        """Display single account move request detail"""
        try:
            move_request_sudo = self._document_check_access(
                "account.move.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = self._account_move_request_get_page_view_values(
            move_request_sudo, access_token, **kw
        )
        return request.render(
            "account_move_request.portal_account_move_request_page", values
        )

    def _account_move_request_get_page_view_values(
        self, move_request, access_token, **kwargs
    ):
        """Prepare values for account move request detail page"""
        values = {
            "move_request": move_request,
            "object": move_request,
            "token": access_token,
            "report_type": "html",
        }
        return self._get_page_view_values(
            move_request,
            access_token,
            values,
            "my_account_move_requests_history",
            False,
            **kwargs
        )

    @http.route(
        ["/my/account_move_request/<int:request_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_account_move_request_report(
        self,
        request_id=None,
        access_token=None,
        report_type="html",
        download=False,
        **kw
    ):
        """Render HTML or PDF report"""
        try:
            move_request_sudo = self._document_check_access(
                "account.move.request", request_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            # Render HTML report directly from template
            html = request.env["ir.qweb"]._render(
                "account_move_request.report_account_move_request",
                {"docs": move_request_sudo},
            )
            return request.make_response(html)

        elif report_type == "pdf":
            # Generate PDF
            report = request.env.ref(
                "account_move_request.action_report_account_move_request"
            )
            pdf, _ = report._render_qweb_pdf(move_request_sudo.ids)

            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
            ]

            if download:
                pdfhttpheaders.append(
                    (
                        "Content-Disposition",
                        f"attachment; filename={move_request_sudo._get_report_base_filename()}.pdf;",
                    )
                )

            return request.make_response(pdf, headers=pdfhttpheaders)
