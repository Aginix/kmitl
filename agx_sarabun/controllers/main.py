# -*- coding: utf-8 -*-
"""Backend PDF serve for the official record (auth=user; honours Route visibility).

Serves the frozen ฉบับลงนาม once completed, or a live preview before that — every
path routes through ``sarabun.document._get_official_pdf()`` (DESIGN §5.4). Portal
(public/magic-link) acting and sharing is phase-2.
"""
from odoo import http
from odoo.http import content_disposition, request


class SarabunDocumentController(http.Controller):

    @http.route(
        ["/sarabun/document/<int:doc_id>/pdf"],
        type="http", auth="user", website=False,
    )
    def sarabun_document_pdf(self, doc_id, inline=None, **kw):
        doc = request.env["sarabun.document"].browse(doc_id)
        # Honour Route visibility (record rules); raises if not allowed.
        doc.check_access_rights("read")
        doc.check_access_rule("read")
        pdf = doc._get_official_pdf()
        filename = (doc._get_report_base_filename() or "sarabun") + ".pdf"
        # `inline` (the in-form / dialog <iframe> preview) renders in the browser;
        # the default forces a download. content_disposition() RFC-6266-encodes the
        # filename (filename*=UTF-8''…) so a Thai เรื่อง is header-safe — never hand-
        # build 'filename="<thai>"', which crashes on the latin-1 header (502).
        disposition = content_disposition(
            filename, "inline" if inline else "attachment"
        )
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                ("Content-Disposition", disposition),
            ],
        )
