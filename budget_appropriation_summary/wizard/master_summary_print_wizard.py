import base64
import io
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MasterSummaryPrintWizard(models.TransientModel):
    _name = "budget.appropriation.master.summary.print.wizard"
    _description = "พิมพ์เล่มแยกหน่วยงาน"

    master_summary_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary",
        string="สรุปภาพรวมสถาบัน",
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.One2many(
        comodel_name="budget.appropriation.master.summary.print.wizard.line",
        inverse_name="wizard_id",
        string="หน่วยงาน",
    )
    select_all = fields.Boolean(
        string="เลือกทั้งหมด",
        default=True,
        help="ติ๊ก/เอาออก เพื่อเลือกหรือยกเลิกทุกหน่วยงานพร้อมกัน",
    )

    @api.onchange("select_all")
    def _onchange_select_all(self):
        for line in self.line_ids:
            line.include = self.select_all

    def action_print(self):
        self.ensure_one()
        # Persist code pages so they are remembered for next time.
        for line in self.line_ids:
            if line.compilation_id.code_page != line.code_page:
                line.compilation_id.code_page = line.code_page

        compilations = self.line_ids.filtered("include").mapped("compilation_id")
        if not compilations:
            raise ValidationError(_("กรุณาเลือกอย่างน้อยหนึ่งหน่วยงาน"))

        return self._print_separate(compilations)

    def _base_filename(self):
        """``budget-by-unit-<slug>`` (no extension), ASCII-safe."""
        name = self.master_summary_id._get_pdf_filename()  # budget-summary-<slug>.pdf
        name = name[: -len(".pdf")] if name.endswith(".pdf") else name
        return name.replace("budget-summary-", "budget-by-unit-", 1)

    def _download_action(self, filename, content, mimetype):
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(content),
                "res_model": "budget.appropriation.master.summary",
                "res_id": self.master_summary_id.id,
                "mimetype": mimetype,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }

    def _print_separate(self, compilations):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            seq = 0
            for compilation in compilations:
                book = compilation._build_department_book_pdf()
                if not book:
                    continue
                seq += 1
                archive.writestr(self._book_entry_name(compilation, seq), book)
            if not seq:
                raise ValidationError(_("ไม่มีข้อมูลให้พิมพ์"))
        return self._download_action(
            "%s.zip" % self._base_filename(), buffer.getvalue(), "application/zip"
        )

    @staticmethod
    def _book_entry_name(compilation, seq):
        """``NN-<code_page>-<dept_code>-<dept_name>.pdf`` (UTF-8, Thai OK)."""
        dept = compilation.department_analytic_id
        name = (dept.name or "").strip()
        for bad in '/\\:*?"<>|':  # strip filesystem-unsafe chars, keep Thai
            name = name.replace(bad, "-")
        parts = [
            "%02d" % seq,
            compilation.code_page or "X",
            dept.code or str(compilation.id),
        ]
        if name:
            parts.append(name)
        return "-".join(parts) + ".pdf"


class MasterSummaryPrintWizardLine(models.TransientModel):
    _name = "budget.appropriation.master.summary.print.wizard.line"
    _description = "บรรทัดพิมพ์เล่มแยกหน่วยงาน"
    _order = "id"

    wizard_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary.print.wizard",
        required=True,
        ondelete="cascade",
    )
    compilation_id = fields.Many2one(
        comodel_name="budget.appropriation.compilation",
        string="รวมเล่มหน่วยงาน",
        required=True,
        readonly=True,
    )
    department_analytic_id = fields.Many2one(
        related="compilation_id.department_analytic_id",
        string="หน่วยงาน",
        readonly=True,
    )
    code_page = fields.Char(string="รหัสหน้า")
    include = fields.Boolean(string="พิมพ์", default=True)
