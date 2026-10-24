# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import content_disposition, request

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class StudentImportTemplate(http.Controller):
    @http.route("/disbursement_student_import/template", type="http", auth="user")
    def template(self):
        content = request.env["disbursement.student.import"]._template_xlsx()
        return request.make_response(
            content,
            headers=[
                ("Content-Type", XLSX),
                (
                    "Content-Disposition",
                    content_disposition("student_import_template.xlsx"),
                ),
            ],
        )
