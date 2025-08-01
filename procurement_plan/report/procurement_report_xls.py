
from odoo import models


class ProcurementXlsx(models.AbstractModel):
    _name = 'report.procurement_plan.report_procurement_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        "generate xlsx"
        thai_months = {
        '1': 'มกราคม', '2': 'กุมภาพันธ์', '3': 'มีนาคม', '4': 'เมษายน',
        '5': 'พฤษภาคม', '6': 'มิถุนายน', '7': 'กรกฎาคม', '8': 'สิงหาคม',
        '9': 'กันยายน', '10': 'ตุลาคม', '11': 'พฤศจิกายน', '12': 'ธันวาคม',
        }

        sheet = workbook.add_worksheet('Procurement Plan')
        sheet.set_zoom(90)

        column_widths = [5, 30, 10, 10, 10, 15, 15, 15, 15, 15, 15, 15, 10, 10, 15, 15, 20, 20, 20, 25, 25]
        for i, width in enumerate(column_widths):
            sheet.set_column(i, i, width)

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
            'bg_color': '#DCE6F1',
        })

        content_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        sheet.merge_range('A1:A2', 'แผน/ผล', header_format)
        sheet.merge_range('B1:B2', 'รายการ', header_format)
        sheet.merge_range('C1:E1', 'รายละเอียดงบประมาณ', header_format)
        sheet.merge_range('F1:F2', 'วิธีการ\nจัดซื้อจัดจ้าง', header_format)
        sheet.merge_range('G1:G2', 'จัดทำ พ.1', header_format)
        sheet.merge_range('H1:J1', 'การจัดซื้อจัดจ้าง', header_format)
        sheet.merge_range('K1:K2', 'เริ่ม\nดำเนินการ', header_format)
        sheet.merge_range('L1:L2', 'แล้วเสร็จ', header_format)
        sheet.merge_range('M1:P1', 'การเบิกจ่ายเงิน', header_format)
        sheet.merge_range('Q1:R1', 'หมายเหตุ', header_format)
        sheet.merge_range('S1:S2', 'เหตุผล', header_format)

        sheet.write('C2', 'จำนวน', header_format)
        sheet.write('D2', 'หน่วยนับ', header_format)
        sheet.write('E2', 'วงเงินรวม', header_format)
        sheet.write('H2', 'ประกาศ\nประกวด\nราคาแบบ', header_format)
        sheet.write('I2', 'อนุมัติผล\n(รอลงนาม\nสัญญา)', header_format)
        sheet.write('J2', 'ลงนาม\nสัญญา', header_format)
        sheet.write('M2', 'งวดงาน', header_format)
        sheet.write('N2', 'จำนวนวัน', header_format)
        sheet.write('O2', 'วันส่งมอบงาน', header_format)
        sheet.write('P2', 'จำนวนเงิน', header_format)
        sheet.write('Q2', 'เลขที่สัญญา', header_format)
        sheet.write('R2', 'เลขที่เบิกจ่าย', header_format)

        row = 2
        for line in lines:
            sheet.write(row, 0, "ผล" or '', content_format)
            sheet.write(row, 1, line.name or '', content_format)
            sheet.write(row, 2, line.amount or '', content_format)
            sheet.write(row, 3, line.unit or '', content_format)
            sheet.write(row, 4, line.total_price or '', content_format)
            sheet.write(row, 5, line.procurement_method_id.name or '', content_format)
            sheet.write(row, 6, thai_months.get(line.purchase_request_eta, '') or '', content_format)
            sheet.write(row, 7, thai_months.get(line.procurement_announcement_eta, '') or '', content_format)
            sheet.write(row, 8, thai_months.get(line.approval_signing_eta, '') or '', content_format)
            sheet.write(row, 9, thai_months.get(line.contract_order_signing_eta, '') or '', content_format)
            sheet.write(row, 10, thai_months.get(line.acceptance_eta, '') or '', content_format)
            sheet.write(row, 11, thai_months.get(line.acceptance_eta, '') or '', content_format)
            sheet.write(row, 16, "Name1" or '', content_format)
            sheet.write(row, 17, "Name1" or '', content_format)
            sheet.write(row, 18, "Name1" or '', content_format)
            sum_days = 0
            sum_amount = 0
            for payment in line.payment_ids:
                sheet.write(row, 12, payment.number or '', content_format)
                sheet.write(row, 13, payment.number_of_days or '', content_format)
                sheet.write(row, 14, thai_months.get(payment.month, '') or '', content_format)
                sheet.write(row, 15, payment.amount or '', content_format)
                sum_days += payment.number_of_days
                sum_amount += payment.amount
                row += 1
            sheet.write(row, 13, sum_days or '', content_format)
            sheet.write(row, 15, sum_amount or '', content_format)
            row += 1

