# -*- coding: utf-8 -*-
import io

from odoo import models


class AssetDepreciationReportXlsx(models.AbstractModel):
    _name = "report.asset.depreciation.xlsx"
    _description = "Asset Depreciation Report XLSX"

    def generate_xlsx(self, wizard):
        try:
            import xlsxwriter
        except ImportError:
            raise ImportError("xlsxwriter is required to generate XLSX reports.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("รายงาน")

        # ---- Formats ----
        title_fmt = workbook.add_format({
            "bold": True, "font_size": 14, "align": "center", "valign": "vcenter",
        })
        subtitle_fmt = workbook.add_format({
            "bold": True, "font_size": 12, "align": "center", "valign": "vcenter",
        })
        info_fmt = workbook.add_format({
            "font_size": 10, "align": "left", "valign": "vcenter",
        })
        header_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "align": "center", "valign": "vcenter",
            "border": 1, "text_wrap": True, "bg_color": "#D9E1F2",
        })
        data_fmt = workbook.add_format({
            "font_size": 10, "align": "left", "valign": "vcenter", "border": 1,
        })
        num_fmt = workbook.add_format({
            "font_size": 10, "align": "right", "valign": "vcenter", "border": 1,
            "num_format": "#,##0.00",
        })
        date_fmt = workbook.add_format({
            "font_size": 10, "align": "center", "valign": "vcenter", "border": 1,
            "num_format": "dd/mm/yyyy",
        })
        total_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "align": "right", "valign": "vcenter",
            "border": 1, "num_format": "#,##0.00",
        })
        sum_label_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "align": "left", "valign": "vcenter",
        })
        sum_num_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "align": "right", "valign": "vcenter",
            "num_format": "#,##0.00",
        })
        sum_unit_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "align": "left", "valign": "vcenter",
        })

        # ---- Column widths (A=0 .. L=11) ----
        col_widths = [6, 16, 30, 14, 10, 10, 14, 14, 14, 14, 14, 24]
        for i, w in enumerate(col_widths):
            sheet.set_column(i, i, w)

        last_col = 11  # column L (0-indexed)

        # ---- Header section (rows 0-7) ----
        sheet.set_row(0, 24)
        sheet.merge_range(0, 0, 0, last_col,
                          "รายงานสำรวจทรัพย์สินและค่าเสื่อมราคา", title_fmt)
        sheet.set_row(1, 20)
        sheet.merge_range(1, 0, 1, last_col,
                          "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง", subtitle_fmt)

        fy = wizard.account_fiscal_year_id
        fy_name = fy.name if fy else "-"
        profile_name = wizard.profile_id.name if wizard.profile_id else "ทั้งหมด"
        source_of_asset_labels = {
            "procurement": "จัดซื้อจัดจ้าง", "donation": "รับบริจาค", "transfer": "รับโอน",
        }
        source_of_asset_name = source_of_asset_labels.get(wizard.source_of_asset, "ทั้งหมด")
        source_name = wizard.source_analytic_id.name if wizard.source_analytic_id else "ทั้งหมด"
        dept_name = wizard.department_analytic_id.complete_name if wizard.department_analytic_id else "ทุกหน่วยงาน"

        info_rows = [
            f"ประเภท: {profile_name}",
            f"ที่มา: {source_of_asset_name}",
            f"แหล่งเงิน: {source_name}",
            f"หน่วยงาน: {dept_name}",
            f"ปีงบประมาณ: {fy_name}",
            f"ประจำวันที่: {wizard.date.strftime('%d/%m/%Y') if wizard.date else '-'}",
        ]
        for i, text in enumerate(info_rows):
            row = 2 + i
            sheet.set_row(row, 16)
            sheet.merge_range(row, 0, row, last_col, text, info_fmt)

        # ---- Column headers (rows 8-9) ----
        header_row1 = 8
        header_row2 = 9
        sheet.set_row(header_row1, 30)
        sheet.set_row(header_row2, 30)

        # Columns that span both rows
        single_headers = [
            (0, "ลำดับ"),
            (1, "รหัสทรัพย์สิน"),
            (2, "ชื่อทรัพย์สิน"),
            (3, "ว.ด.ป. ที่ได้มา"),
            (4, "อายุสุทธิ (วัน)"),
            (5, "อายุใช้งาน"),
            (6, "ราคาทุน"),
            (7, "ค่าเสื่อมราคาต่อปี"),
            (11, "หน่วยงานรับผิดชอบ"),
        ]
        for col, label in single_headers:
            sheet.merge_range(header_row1, col, header_row2, col, label, header_fmt)

        # Merged header for ค่าเสื่อมสะสม (cols 8-10)
        sheet.merge_range(header_row1, 8, header_row1, 10, "ค่าเสื่อมสะสม", header_fmt)
        sheet.write(header_row2, 8, "ยกมา", header_fmt)
        sheet.write(header_row2, 9, "เดือนนี้", header_fmt)
        sheet.write(header_row2, 10, "ยกไป", header_fmt)

        # ---- Data rows ----
        assets = wizard._get_assets()
        data_start_row = 10
        row = data_start_row

        fy_date_from = fy.date_from if fy else None
        fy_date_to = fy.date_to if fy else None
        wizard_date = wizard.date

        total_purchase = 0.0
        total_depr_year = 0.0
        total_depr_before = 0.0
        total_depr_this_month = 0.0
        total_depr_carry = 0.0
        total_book_oct = 0.0
        total_book_sep = 0.0

        for seq, asset in enumerate(assets, start=1):
            depr_lines = asset.depreciation_line_ids.filtered(
                lambda l: l.type == "depreciate"
            )

            # Col H: depreciation lines within fiscal year
            depr_year = sum(
                l.amount for l in depr_lines
                if fy_date_from and fy_date_to and fy_date_from <= l.line_date <= fy_date_to
            )

            # Col I: accumulated before start of wizard month
            month_start = wizard_date.replace(day=1) if wizard_date else None
            depr_before = sum(
                l.amount for l in depr_lines
                if month_start and l.line_date < month_start
            )

            # Col J: depreciation in wizard month
            depr_this_month = sum(
                l.amount for l in depr_lines
                if wizard_date and l.line_date.year == wizard_date.year
                and l.line_date.month == wizard_date.month
            )

            # Col K
            depr_carry = depr_before + depr_this_month

            # Book value ต.ค. (start of fiscal year)
            depr_before_fy = sum(
                l.amount for l in depr_lines
                if fy_date_from and l.line_date < fy_date_from
            )
            book_oct = (asset.purchase_value or 0.0) - depr_before_fy

            # Book value ก.ย. (end of fiscal year)
            depr_up_to_fy_end = sum(
                l.amount for l in depr_lines
                if fy_date_to and l.line_date <= fy_date_to
            )
            book_sep = (asset.purchase_value or 0.0) - depr_up_to_fy_end

            # Age in days
            if wizard_date and asset.date_start:
                age_days = (wizard_date - asset.date_start).days
            else:
                age_days = 0

            sheet.set_row(row, 16)
            sheet.write(row, 0, seq, data_fmt)
            sheet.write(row, 1, asset.number or asset.code or "", data_fmt)
            sheet.write(row, 2, asset.name or "", data_fmt)
            if asset.date_start:
                sheet.write_datetime(row, 3, asset.date_start, date_fmt)
            else:
                sheet.write(row, 3, "", data_fmt)
            sheet.write(row, 4, age_days, data_fmt)
            sheet.write(row, 5, asset.method_number or 0, data_fmt)
            sheet.write(row, 6, asset.purchase_value or 0.0, num_fmt)
            sheet.write(row, 7, depr_year, num_fmt)
            sheet.write(row, 8, depr_before, num_fmt)
            sheet.write(row, 9, depr_this_month, num_fmt)
            sheet.write(row, 10, depr_carry, num_fmt)
            sheet.write(row, 11, asset.department_analytic_id.complete_name if asset.department_analytic_id else "", data_fmt)

            total_purchase += asset.purchase_value or 0.0
            total_depr_year += depr_year
            total_depr_before += depr_before
            total_depr_this_month += depr_this_month
            total_depr_carry += depr_carry
            total_book_oct += book_oct
            total_book_sep += book_sep
            row += 1

        # ---- Footer / totals ----
        sheet.set_row(row, 16)
        sheet.merge_range(row, 0, row, 5, "รวม", total_fmt)
        sheet.write(row, 6, total_purchase, total_fmt)
        sheet.write(row, 7, total_depr_year, total_fmt)
        for col in range(8, last_col + 1):
            sheet.write(row, col, "", total_fmt)
        row += 2  # blank row separator

        # ---- Summary rows ----
        summary_items = [
            ("ยอดรวม ราคาทุนรวม", total_purchase),
            ("ยอดรวม ค่าเสื่อมราคา : ปี", total_depr_year),
            ("ยอดรวม ค่าเสื่อมราคาสะสม (ยกมา)", total_depr_before),
            ("ยอดรวม ค่าเสื่อมราคาสะสม (เดือนนี้)", total_depr_this_month),
            ("ยอดรวม ค่าเสื่อมราคาสะสม (ยกไป)", total_depr_carry),
            ("ยอดรวม ราคาตามบัญชี [ ต.ค. ]", total_book_oct),
            ("ยอดรวม ราคาตามบัญชี [ ก.ย. ]", total_book_sep),
        ]
        for label, value in summary_items:
            sheet.set_row(row, 18)
            sheet.merge_range(row, 0, row, 8, label, sum_label_fmt)
            sheet.merge_range(row, 9, row, 10, value, sum_num_fmt)
            sheet.write(row, 11, "บาท", sum_unit_fmt)
            row += 1

        workbook.close()
        return output.getvalue()
