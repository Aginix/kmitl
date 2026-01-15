# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools.translate import _


class SarabunDocumentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add sarabun document count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if "sarabun_document_count" in counters:
            sarabun_document_count = (
                request.env["sarabun.document"].search_count([])
                if request.env["sarabun.document"].check_access_rights(
                    "read", raise_exception=False
                )
                else 0
            )
            values["sarabun_document_count"] = sarabun_document_count
        return values

    @http.route(
        ["/my/sarabun_documents", "/my/sarabun_documents/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_sarabun_documents(self, page=1, sortby=None, filterby=None, **kw):
        """Display sarabun documents in portal."""
        values = self._prepare_portal_layout_values()
        SarabunDocument = request.env["sarabun.document"]

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
        sarabun_document_count = SarabunDocument.search_count(domain)
        pager = portal_pager(
            url="/my/sarabun_documents",
            total=sarabun_document_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )

        # Content
        sarabun_documents = SarabunDocument.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values.update(
            {
                "sarabun_documents": sarabun_documents,
                "page_name": "sarabun_document",
                "pager": pager,
                "default_url": "/my/sarabun_documents",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("agx_sarabun_portal.portal_my_sarabun_documents", values)

    @http.route(
        ["/my/sarabun_document/<int:document_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_sarabun_document(self, document_id, report_type=None, access_token=None, message=False, download=False, **kw):
        """Display single sarabun document in portal."""
        try:
            sarabun_document_sudo = self._document_check_access(
                "sarabun.document", document_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=sarabun_document_sudo, report_type=report_type, report_ref='agx_sarabun_report.action_report_sarabun_documents', download=download)

        values = self._sarabun_document_get_page_view_values(sarabun_document_sudo, access_token, **kw)
        return request.render("agx_sarabun_portal.portal_sarabun_document_page", values)

    def _sarabun_document_get_page_view_values(self, sarabun_document, access_token, **kwargs):
        values = {
            "sarabun_document": sarabun_document,
            "page_name": "sarabun_document",
            "report_type": "html",
        }
        return self._get_page_view_values(sarabun_document, access_token, values, 'my_sarabun_documents', False, **kwargs)

    @http.route(
        ["/my/sarabun_document/<int:document_id>/<string:report_type>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_sarabun_document_report(
        self, document_id, report_type, access_token=None, **kw
    ):
        """Render sarabun document report in HTML or PDF format."""
        try:
            sarabun_document_sudo = self._document_check_access(
                "sarabun.document", document_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type == "html":
            # Render HTML report directly
            report = request.env.ref("agx_sarabun_report.report_sarabun_document_template")
            html = request.env["ir.actions.report"]._render_qweb_html(
                report.id, [sarabun_document_sudo.id]
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
            report = request.env.ref("agx_sarabun_report.report_sarabun_document_template")
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [sarabun_document_sudo.id]
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    f'inline; filename="Sarabun Document - {sarabun_document_sudo.name}.pdf"',
                ),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
