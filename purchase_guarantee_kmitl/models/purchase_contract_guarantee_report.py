from odoo import fields, models, tools


class PurchaseContractGuaranteeReport(models.Model):
    _name = "purchase.contract.guarantee.report"
    _description = "Contract Guarantee Register Report"
    _auto = False
    _order = "purchase_id desc"

    # --- Dimensions ---
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order", readonly=True)
    contract_number = fields.Char(string="Contract Number", readonly=True)
    contract_name = fields.Char(string="Contract Name", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    contract_type_id = fields.Many2one("purchase.contract.type", string="Contract Type", readonly=True)
    work_start = fields.Date(string="Work Start", readonly=True)
    work_end = fields.Date(string="Work End", readonly=True)
    purchase_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("purchase", "Purchase Order"),
            ("done", "Closed"),
            ("cancel", "Cancelled"),
        ],
        string="Contract Status",
        readonly=True,
    )
    guarantee_type_id = fields.Many2one("purchase.guarantee.type", string="Guarantee Type", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    date_due_guarantee = fields.Date(string="Guarantee Due Date", readonly=True)
    date_due_display = fields.Char(string="Guarantee Expiry", readonly=True)
    date_return = fields.Date(string="Guarantee Return Date", readonly=True)
    guarantee_return_state = fields.Selection(
        selection=[("returned", "Returned"), ("pending", "Pending")],
        string="Guarantee Return Status",
        readonly=True,
    )

    # --- Measures ---
    amount = fields.Monetary(string="Guarantee Amount", readonly=True)
    amount_returned = fields.Monetary(string="Returned Guarantee Amount", readonly=True)
    guarantee_count = fields.Integer(string="Guarantee Count", readonly=True)
    amount_total = fields.Monetary(string="Contract Amount", readonly=True)
    fines_late = fields.Monetary(string="Fines Amount", readonly=True)
    contract_period_days = fields.Integer(string="Contract Period Days", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    g.id                    AS id,
                    g.purchase_id           AS purchase_id,
                    po.contract_number      AS contract_number,
                    po.contract_name        AS contract_name,
                    g.partner_id            AS partner_id,
                    po.contract_type_id     AS contract_type_id,
                    po.work_start           AS work_start,
                    po.work_end             AS work_end,
                    po.state                AS purchase_state,
                    g.guarantee_type_id     AS guarantee_type_id,
                    po.currency_id          AS currency_id,
                    g.date_due_guarantee    AS date_due_guarantee,
                    CASE
                        WHEN g.date_due_guarantee IS NOT NULL
                            THEN TO_CHAR(g.date_due_guarantee, 'DD/MM/YYYY')
                        ELSE 'จนกว่าจะพ้นภาระผูกพันธ์'
                    END                     AS date_due_display,
                    g.date_return           AS date_return,
                    CASE
                        WHEN g.date_return IS NOT NULL THEN 'returned'
                        ELSE 'pending'
                    END                     AS guarantee_return_state,
                    g.amount                AS amount,
                    COALESCE((
                        SELECT SUM(am.amount_total) - SUM(am.amount_residual)
                        FROM account_move_return_guarantee_rel rel
                        JOIN account_move am ON am.id = rel.move_id
                        WHERE rel.guarantee_id = g.id
                    ), 0)                   AS amount_returned,
                    1                       AS guarantee_count,
                    po.amount_total         AS amount_total,
                    po.fines_late           AS fines_late,
                    po.contract_period_days AS contract_period_days
                FROM purchase_guarantee g
                JOIN purchase_order po ON po.id = g.purchase_id
                JOIN purchase_guarantee_method pgm ON pgm.id = g.guarantee_method_id
                WHERE pgm.default_for_model = 'purchase.order.po'
                  AND g.active = TRUE
            )
            """
            % self._table
        )
