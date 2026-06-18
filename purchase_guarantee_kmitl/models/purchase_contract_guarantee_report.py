from odoo import fields, models, tools


class PurchaseContractGuaranteeReport(models.Model):
    _name = "purchase.contract.guarantee.report"
    _description = "รายงานทะเบียนคุมสัญญา"
    _auto = False
    _order = "purchase_id desc"

    purchase_id = fields.Many2one("purchase.order", string="ใบสั่งซื้อ/จ้าง", readonly=True)
    contract_number = fields.Char(string="เลขที่สัญญา", readonly=True)
    contract_name = fields.Char(string="ชื่องาน", readonly=True)
    partner_id = fields.Many2one("res.partner", string="คู่ค้า", readonly=True)
    contract_type_id = fields.Many2one("purchase.contract.type", string="ประเภทงาน", readonly=True)
    work_start = fields.Date(string="วันที่เริ่มสัญญา", readonly=True)
    work_end = fields.Date(string="วันที่สิ้นสุดสัญญา", readonly=True)
    purchase_state = fields.Selection(
        selection=[
            ("draft", "Draft RFQ"),
            ("sent", "RFQ Sent"),
            ("purchase", "Purchase Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="สถานะสัญญา",
        readonly=True,
    )
    guarantee_type_id = fields.Many2one("purchase.guarantee.type", string="ประเภทหลักประกัน", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    date_due_display = fields.Char(string="วันที่สิ้นสุดอายุหลักประกัน", readonly=True)
    guarantee_return_state = fields.Selection(
        selection=[("returned", "คืนแล้ว"), ("pending", "ยังไม่ได้คืน")],
        string="สถานะหลักประกัน",
        readonly=True,
    )
    amount = fields.Monetary(string="มูลค่าหลักประกัน", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    g.id                AS id,
                    g.purchase_id       AS purchase_id,
                    po.contract_number  AS contract_number,
                    po.contract_name    AS contract_name,
                    g.partner_id        AS partner_id,
                    po.contract_type_id AS contract_type_id,
                    po.work_start       AS work_start,
                    po.work_end         AS work_end,
                    po.state            AS purchase_state,
                    g.guarantee_type_id AS guarantee_type_id,
                    po.currency_id      AS currency_id,
                    CASE
                        WHEN g.date_due_guarantee IS NOT NULL
                            THEN TO_CHAR(g.date_due_guarantee, 'DD/MM/YYYY')
                        ELSE 'จนกว่าจะพ้นภาระผูกพันธ์'
                    END                 AS date_due_display,
                    CASE
                        WHEN g.date_return IS NOT NULL THEN 'returned'
                        ELSE 'pending'
                    END                 AS guarantee_return_state,
                    g.amount            AS amount
                FROM purchase_guarantee g
                JOIN purchase_order po ON po.id = g.purchase_id
                JOIN purchase_guarantee_method pgm ON pgm.id = g.guarantee_method_id
                WHERE pgm.default_for_model = 'purchase.order.po'
                  AND g.active = TRUE
            )
            """
            % self._table
        )
