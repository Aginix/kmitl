from odoo import models


class ProcurementXlsx(models.AbstractModel):
    _name = 'report.procurement_plan.report_procurement_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet('Procurement Plan')
        sheet.set_zoom(90)

        # กำหนดความกว้างของคอลัมน์
        column_widths = [5, 15, 30, 10, 10, 15, 15, 15, 15, 15, 15, 15, 10, 10, 15, 15, 20, 20, 20, 25, 25]
        for i, width in enumerate(column_widths):
            sheet.set_column(i, i, width)

        # ฟอร์แมต
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
            'bg_color': '#DCE6F1',
        })

        # แถว 1: หัวข้อใหญ่
        sheet.merge_range('A1:S1', 'แผนการดำเนินการจัดซื้อ/จัดจ้าง ประจำปีงบประมาณ พ.ศ. 2569', header_format)
        sheet.merge_range('T1:U1', 'ที่ดินและสิ่งก่อสร้างที่มีราคาต่อหน่วยสูงกว่า 2 ล้านบาท', header_format)

        # แถว 2: หัวข้อย่อย
        headers_row_2 = [
            'แผน/ผล', 'รายการ', 'รายละเอียดงบประมาณ', '', '', 'วิธีการ\nจัดซื้อจัดจ้าง', 'จัดทำ พ.1',
            'การจัดซื้อจัดจ้าง', '', '', 'เริ่ม\nดำเนินการ', 'แล้วเสร็จ', 'การเบิกจ่ายเงิน', '', '', '', 'หมายเหตุ'
        ]
        # Merge คอลัมน์ที่เหมือนกัน
        sheet.write('A2', 'แผน/ผล', header_format)
        sheet.write('B2', 'รายการ', header_format)
        sheet.merge_range('C2:E2', 'รายละเอียดงบประมาณ', header_format)
        sheet.write('F2', 'วิธีการ\nจัดซื้อจัดจ้าง', header_format)
        sheet.write('G2', 'จัดทำ พ.1', header_format)
        sheet.merge_range('H2:J2', 'การจัดซื้อจัดจ้าง', header_format)
        sheet.write('K2', 'เริ่ม\nดำเนินการ', header_format)
        sheet.write('L2', 'แล้วเสร็จ', header_format)
        sheet.merge_range('M2:Q2', 'การเบิกจ่ายเงิน', header_format)
        sheet.write('R2', 'หมายเหตุ', header_format)
        sheet.write('S2', '', header_format)  # เผื่อขยาย

        sheet.write('T2', 'เลขที่สัญญา', header_format)
        sheet.write('U2', 'เลขที่เบิกจ่าย', header_format)

        # แถว 3: หัวข้อที่เจาะจง
        headers_row_3 = [
            '', '', 'จำนวน', 'หน่วยนับ', 'วงเงินรวม', '', '',
            'ประกาศ\nประกวด\nราคาแบบ', 'อนุมัติผล\n(รอลงนาม\nสัญญา)', 'ลงนาม\nสัญญา',
            '', '', 'งวดงาน', 'จำนวนวัน', 'วันส่งมอบงาน', 'จำนวนเงิน', '', ''
        ]
        sheet.write('C3', 'จำนวน', header_format)
        sheet.write('D3', 'หน่วยนับ', header_format)
        sheet.write('E3', 'วงเงินรวม', header_format)
        sheet.write('H3', 'ประกาศ\nประกวด\nราคาแบบ', header_format)
        sheet.write('I3', 'อนุมัติผล\n(รอลงนาม\nสัญญา)', header_format)
        sheet.write('J3', 'ลงนาม\nสัญญา', header_format)
        sheet.write('M3', 'งวดงาน', header_format)
        sheet.write('N3', 'จำนวนวัน', header_format)
        sheet.write('O3', 'วันส่งมอบงาน', header_format)
        sheet.write('P3', 'จำนวนเงิน', header_format)

        # เพิ่มข้อมูลในแถวถัดไป (สมมติว่ามี lines เป็น recordset)
        content_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        row = 3  # เริ่มที่แถวถัดไป
        for line in lines:
            sheet.write(row, 0, "Name1" or '', content_format)
            sheet.write(row, 1, "Name2" or '', content_format)
            sheet.write(row, 2, "Name3" or '', content_format)
            sheet.write(row, 3, "Name4" or '', content_format)
            sheet.write(row, 4, "Name1" or '', content_format)
            # เติมช่องอื่นๆ ตามข้อมูลที่คุณมีในแต่ละ field
            row += 1

