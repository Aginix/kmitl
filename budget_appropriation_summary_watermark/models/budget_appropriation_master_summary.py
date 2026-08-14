from odoo import fields, models


class BudgetAppropriationMasterSummary(models.Model):
    _inherit = "budget.appropriation.master.summary"

    passed_council = fields.Boolean(
        string="ผ่านสภา",
        tracking=True,
        help="ระบุว่าสรุปภาพรวมงบประมาณสถาบันนี้ผ่านการพิจารณาของสภาสถาบันแล้ว",
    )
    watermark_text = fields.Char(
        string="ข้อความลายน้ำ",
        default="เอกสารพิมพ์จากระบบ",
        help="ข้อความลายน้ำที่จะพิมพ์ทับบนรายงาน PDF (เว้นว่างเพื่อไม่ให้มีลายน้ำ)",
    )

    def action_print_report_watermark(self):
        """Print the combined PDF with the text watermark stamped on every page.

        Reuses the base ``action_print_report`` but injects the watermark text
        into the context so ``ir.actions.report._get_watermark`` picks it up for
        this print path only (the plain print button stays watermark-free).
        """
        self.ensure_one()
        return self.with_context(
            budget_watermark_text=self.watermark_text or ""
        ).action_print_report()
