# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BudgetCompilationF24Controller(http.Controller):

    @http.route(
        "/budget_appropriation_summary/compilation/<int:compilation_id>/f24/<string:report_type>",
        type="http",
        auth="user",
        website=True,
    )
    def compilation_f24_report(self, compilation_id, report_type, **kw):
        record = request.env["budget.appropriation.compilation"].browse(compilation_id)
        if not record.exists():
            return request.redirect("/web")

        report = request.env.ref(
            "budget_appropriation_summary_f24.action_report_compilation_f24"
        )

        if report_type == "html":
            html = (
                request.env["ir.actions.report"]
                .with_context(html_preview=True)
                ._render_qweb_html(
                    report.id,
                    [record.id],
                    data={"title": f"{record.name} - F24"},
                )[0]
            )
            return request.make_response(
                html,
                headers=[
                    ("Content-Type", "text/html"),
                    ("Content-Length", len(html)),
                ],
            )
        elif report_type == "pdf":
            pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                report.id, [record.id]
            )
            return request.make_response(
                pdf_content,
                headers=[
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", len(pdf_content)),
                    (
                        "Content-Disposition",
                        f'inline; filename="{record.name} - F24.pdf"',
                    ),
                ],
            )

        return request.redirect("/web")
