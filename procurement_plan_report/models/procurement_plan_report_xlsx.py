# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class ProcurementPlanReportXlsx(models.AbstractModel):
    """XLSX export — shares the compute with the screen (one workbook per form
    type, matching the government template)."""

    _name = "report.procurement_plan_report.report_xlsx"
    _description = "Procurement Plan Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        report = self.env["procurement.plan.report"]
        result = report.get_report_data(options)
        is_equipment = result["is_equipment"]

        # ------------------------------------------------------------------
        # Formats
        # ------------------------------------------------------------------
        title = workbook.add_format({"bold": True, "font_size": 14})
        hdr = workbook.add_format({"bold": True})
        box = workbook.add_format(
            {"bold": True, "align": "center", "valign": "vcenter", "border": 1, "text_wrap": True}
        )
        cell = workbook.add_format({"border": 1, "valign": "vcenter", "text_wrap": True})
        cell_c = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter"}
        )
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        num_b = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )
        tag_plan = workbook.add_format(
            {"border": 1, "bold": True, "align": "center", "valign": "vcenter"}
        )
        tag_actual = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter", "font_color": "#666666"}
        )

        # Columns: [tag, รายการ, (ประเภทครุภัณฑ์), จำนวน, หน่วย, (ราคา/หน่วย),
        #           วงเงินรวม, วิธี, พ.1, ประกาศ, อนุมัติ, ลงนาม, ตรวจรับ,
        #           งวด, จำนวนวัน, เดือน, จำนวนเงิน, หมายเหตุ]
        cols = ["แผน/ผล", "รายการ"]
        if is_equipment:
            cols.append("ประเภทครุภัณฑ์")
        cols += ["จำนวน", "หน่วยนับ"]
        if is_equipment:
            cols.append("ราคาต่อหน่วย")
        cols += [
            "วงเงินรวม",
            "วิธีการจัดซื้อจัดจ้าง",
            "จัดทำ พ.1",
            "ประกาศ",
            "อนุมัติผล",
            "ลงนามสัญญา",
            "ตรวจรับ/ส่งมอบ",
            "งวด",
            "จำนวนวัน",
            "เดือน",
            "จำนวนเงิน",
            "หมายเหตุ",
        ]
        last_col = len(cols) - 1

        sheet = workbook.add_worksheet(result["report_type"][:31])
        sheet.set_landscape()
        sheet.set_column(1, 1, 28)
        sheet.set_column(2, last_col, 12)

        r = 0

        def merge_line(text, fmt=None):
            nonlocal r
            sheet.merge_range(r, 0, r, last_col, text, fmt or hdr)
            r += 1

        merge_line(result["title"], title)
        merge_line(
            "แผนการดำเนินการจัดซื้อ/จัดจ้าง ประจำปีงบประมาณ พ.ศ. %s"
            % result["fiscal_year_name"]
        )
        merge_line(result["expense"])
        merge_line(result["company_name"])

        for group in result["groups"]:
            r += 1
            merge_line("หน่วยงาน : %s" % group["department_name"])
            merge_line("แหล่งเงิน : %s" % group["source_name"])
            merge_line("แผนงาน : %s" % group["program_name"])
            merge_line("ผลผลิต : %s" % group["output_name"])
            merge_line("กิจกรรม : %s" % group["activity_name"])

            for col, name in enumerate(cols):
                sheet.write(r, col, name, box)
            r += 1

            for item in group["items"]:
                r = self._write_item(
                    sheet, r, item, is_equipment,
                    {
                        "cell": cell, "cell_c": cell_c, "num": num, "num_b": num_b,
                        "tag_plan": tag_plan, "tag_actual": tag_actual,
                    },
                )
            r += 1

        # Signature block
        r += 1
        sheet.write(r, 1, "ลงชื่อผู้บันทึกข้อมูล (แผน) ............................", hdr)
        sheet.write(r, max(1, last_col - 3), "ลงชื่อผู้บันทึกข้อมูล (ผล) ............................", hdr)

    def _write_item(self, sheet, r, item, is_equipment, fmt):
        """Write one item: a แผน block then a ผล block (each = a lead row with
        the item detail + first installment, then extra installment rows)."""
        r = self._write_side(sheet, r, item, "แผน", item, is_equipment, fmt, fmt["tag_plan"])
        actual = dict(item["actual"])
        # The actual side reuses the item-level identity (name/qty/category) but
        # its own figures; blanks render as empty cells until the chain fills.
        actual_item = dict(
            item,
            total_price=actual.get("total_price"),
            unit_price=actual.get("unit_price"),
            eta=actual.get("eta") or {},
            installments=actual.get("installments") or [],
            actual=actual,
        )
        r = self._write_side(
            sheet, r, actual_item, "ผล", item, is_equipment, fmt, fmt["tag_actual"]
        )
        return r

    def _write_side(self, sheet, r, data, tag, item, is_equipment, fmt, tag_fmt):
        installments = data.get("installments") or [{}]
        first = installments[0] if installments else {}
        eta = data.get("eta") or {}
        c = 0

        # Lead row (item detail + first installment)
        sheet.write(r, c, tag, tag_fmt); c += 1
        sheet.write(r, c, item["name"], fmt["cell"]); c += 1
        if is_equipment:
            sheet.write(r, c, item["equipment_category"], fmt["cell"]); c += 1
        sheet.write(r, c, item["amount"], fmt["cell_c"]); c += 1
        sheet.write(r, c, item["unit"], fmt["cell_c"]); c += 1
        if is_equipment:
            self._num(sheet, r, c, data.get("unit_price"), fmt); c += 1
        self._num(sheet, r, c, data.get("total_price"), fmt); c += 1
        sheet.write(r, c, item["procurement_method"], fmt["cell"]); c += 1
        for key in ("pr", "announce", "approve", "sign", "accept"):
            sheet.write(r, c, eta.get(key, ""), fmt["cell_c"]); c += 1
        # First installment
        sheet.write(r, c, first.get("number", ""), fmt["cell_c"]); c += 1
        sheet.write(r, c, first.get("days", ""), fmt["cell_c"]); c += 1
        sheet.write(r, c, first.get("month", ""), fmt["cell_c"]); c += 1
        self._num(sheet, r, c, first.get("amount"), fmt); c += 1
        sheet.write(r, c, data.get("contract_no", "") or data.get("reason", ""), fmt["cell"])
        r += 1

        # Extra installment rows (only งวด columns filled)
        inst_col = 2 + (1 if is_equipment else 0) + 2 + (1 if is_equipment else 0) + 2 + 5
        for extra in installments[1:]:
            cc = inst_col
            sheet.write(r, cc, extra.get("number", ""), fmt["cell_c"]); cc += 1
            sheet.write(r, cc, extra.get("days", ""), fmt["cell_c"]); cc += 1
            sheet.write(r, cc, extra.get("month", ""), fmt["cell_c"]); cc += 1
            self._num(sheet, r, cc, extra.get("amount"), fmt)
            r += 1
        return r

    def _num(self, sheet, r, c, value, fmt):
        if value is None or value == "":
            sheet.write(r, c, "", fmt["cell"])
        else:
            sheet.write_number(r, c, value, fmt["num"])
