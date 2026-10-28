# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import content_disposition, request


class DisbursementPrinterController(http.Controller):
    @http.route(
        ["/disbursement/request/<int:request_id>/sarabun_pdf"],
        type="http",
        auth="user",
        website=False,
    )
    def disbursement_sarabun_pdf(self, request_id, **kw):
        """The official PDF of the request's หนังสือ (frozen once completed, else
        live), on the request's read access instead of the หนังสือ's route."""
        if not request.env.user.has_group(
            "disbursement_printer.group_disbursement_printer"
        ):
            raise AccessError(_("You are not allowed to print this."))
        disbursement = request.env["disbursement.request"].browse(request_id)
        disbursement.check_access_rights("read")
        disbursement.check_access_rule("read")
        doc = disbursement._get_printer_sarabun_document()
        if not doc:
            return request.not_found()
        pdf = doc._get_official_pdf()
        filename = (doc._get_report_base_filename() or "sarabun") + ".pdf"
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )
