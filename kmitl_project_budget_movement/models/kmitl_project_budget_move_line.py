from odoo import fields, models, tools


class KmitlProjectBudgetMoveLine(models.Model):
    """Project Budget Movements (การเคลื่อนไหวงบประมาณโครงการ) — one row per
    budget move line on a project's ``kmitl_project`` dimension, so project
    owners follow every movement without any right on ``budget.move(.line)``
    (kmitl_project ADR-0007).

    Rows are posted allocations, budget entries and ตัดงบ plus in-flight
    transfers. A row in another fiscal year is ``other_year``; one in the
    project's year that misses its coordinate (รหัสงบ + four base dims — the
    same one ``budget_amount`` sums) is ``off_target``; neither is counted.
    Posted non-ตัดงบ rows therefore net to the project's ``budget_amount``.
    """

    _name = "kmitl.project.budget.move.line"
    _description = "Project Budget Movement"
    _auto = False
    _order = "date desc, id desc"

    project_id = fields.Many2one("kmitl.project", string="โครงการ", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    move_id = fields.Many2one(
        "budget.move",
        string="Budget Move",
        readonly=True,
        groups="budget.group_budget_viewer",
    )
    commitment_line_id = fields.Many2one("budget.commitment.line", readonly=True)
    name = fields.Char(string="เลขที่เอกสาร", readonly=True)
    source_name = fields.Char(
        string="เอกสารต้นทาง",
        related="commitment_line_id.res_name",
        help="เอกสารที่ตัดงบ (เช่น ใบขอซื้อ / ใบขอเบิก)",
    )
    date = fields.Date(string="วันที่", readonly=True)
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year", string="ปีงบประมาณ", readonly=True
    )
    kind = fields.Selection(
        [
            ("appropriation", "จัดสรร"),
            ("transfer_in", "รับโอนเข้า"),
            ("transfer_out", "โอนออก"),
            ("entry", "บันทึกงบประมาณ"),
            ("consume", "ตัดงบ"),
        ],
        string="ประเภท",
        readonly=True,
    )
    account_id = fields.Many2one("budget.account", string="รหัสงบ", readonly=True)
    counterpart_department_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงานคู่โอน",
        readonly=True,
        help="รับโอนเข้า: ส่วนงานต้นทาง (ผู้สนับสนุน) / โอนออก: ส่วนงานปลายทาง",
    )
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price", readonly=True)
    status = fields.Selection(
        [
            ("posted", "ผ่านแล้ว"),
            ("in_progress", "อยู่ระหว่างดำเนินการ"),
            ("other_year", "ต่างปีงบประมาณ"),
            ("off_target", "พิกัดไม่ตรงกับโครงการ"),
        ],
        string="สถานะ",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW kmitl_project_budget_move_line AS (
                SELECT
                    l.id AS id,
                    p.id AS project_id,
                    p.company_id AS company_id,
                    m.id AS move_id,
                    m.commitment_line_id AS commitment_line_id,
                    COALESCE(t.name, m.name) AS name,
                    m.date AS date,
                    l.account_fiscal_year_id AS account_fiscal_year_id,
                    CASE
                        WHEN m.move_type = 'appropriation' THEN 'appropriation'
                        WHEN m.move_type = 'consume' THEN 'consume'
                        WHEN l.transfer_direction = 'to' THEN 'transfer_in'
                        WHEN l.transfer_direction = 'from' THEN 'transfer_out'
                        ELSE 'entry'
                    END AS kind,
                    l.account_id AS account_id,
                    CASE
                        WHEN t.id IS NOT NULL THEN (
                            SELECT c.department_analytic_id
                            FROM budget_move_line c
                            WHERE c.move_id = l.move_id
                                AND c.transfer_direction <> l.transfer_direction
                            ORDER BY c.id
                            LIMIT 1
                        )
                    END AS counterpart_department_id,
                    l.balance AS amount,
                    CASE
                        WHEN l.account_fiscal_year_id
                            IS DISTINCT FROM p.account_fiscal_year_id
                            THEN 'other_year'
                        WHEN NOT COALESCE(
                            l.account_id = p.budget_account_id
                            AND l.company_id = p.company_id
                            AND p.analytic_distribution
                                ? l.department_analytic_id::text
                            AND p.analytic_distribution ? l.source_analytic_id::text
                            AND p.analytic_distribution ? l.fund_analytic_id::text
                            AND p.analytic_distribution
                                ? l.activity_analytic_id::text,
                            FALSE
                        ) THEN 'off_target'
                        WHEN m.state = 'posted' THEN 'posted'
                        ELSE 'in_progress'
                    END AS status
                FROM budget_move_line l
                JOIN budget_move m ON m.id = l.move_id
                JOIN kmitl_project p
                    ON p.analytic_account_id = l.kmitl_project_analytic_id
                LEFT JOIN budget_transfer t ON t.move_id = m.id
                WHERE m.active
                    AND m.move_type IN ('appropriation', 'entry', 'consume')
                    AND (
                        m.state = 'posted'
                        OR t.state IN ('submitted', 'sent', 'returned')
                    )
            )
            """
        )
