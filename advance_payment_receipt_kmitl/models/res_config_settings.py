from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_return_product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า/บริการสำหรับการคืนเงินยืม",
        config_parameter="advance_payment_receipt_kmitl.return_product_id",
        domain="[('property_account_income_id', '!=', False)]",
        help="สินค้า/บริการที่ใช้เป็นรายการบนใบเสร็จรับเงินคืนยืม "
        "บัญชีรายได้ของใบเสร็จจะดึงจากบัญชีรายได้ของสินค้านี้",
    )

    advance_payment_return_payment_method_id = fields.Many2one(
        comodel_name="kmitl.payment.method",
        string="บัญชีรับโอนเงินคืนยืมเริ่มต้น",
        config_parameter="advance_payment_receipt_kmitl.return_payment_method_id",
        domain="[('payment_type', '=', 'transfer')]",
        help="บัญชีรับโอนที่ใช้ตั้งต้นบนรายการคืนเงิน (เจ้าหน้าที่ปรับแก้ได้ก่อนกด"
        "สร้างใบเสร็จรับเงิน) — คืนยืมรับเป็นเงินโอนเท่านั้น",
    )
