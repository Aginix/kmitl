from odoo import fields, models, tools


class KmitlProjectFunding(models.Model):
    """Funding Summary (เงินสนับสนุนที่ได้รับ) — one row per budget move line on a
    project's ``kmitl_project`` dimension, so project authors see who sent how
    much without any right on ``budget.move(.line)`` (kmitl_project ADR-0007).

    Rows are posted appropriation/entry moves (received) plus in-flight
    transfers (in progress); a row whose line misses the project's full
    coordinate (รหัสงบ + FY + four base dims — the same one ``budget_amount``
    sums) is off-target and counted in neither. Received rows therefore net to
    the project's ``budget_amount``.
    """

    _name = "kmitl.project.funding"
    _description = "Project Funding Summary"
    _auto = False
    _order = "date desc, id desc"

    project_id = fields.Many2one("kmitl.project", string="โครงการ", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    name = fields.Char(string="เลขที่เอกสาร", readonly=True)
    date = fields.Date(string="วันที่", readonly=True)
    direction = fields.Selection(
        [("to", "รับโอนเข้า"), ("from", "โอนออก")],
        string="ทิศทาง",
        readonly=True,
    )
    account_id = fields.Many2one("budget.account", string="รหัสงบ", readonly=True)
    counterpart_department_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงานคู่โอน",
        readonly=True,
        help="รับโอนเข้า: ส่วนงานต้นทาง (ผู้สนับสนุน) / โอนออก: ส่วนงานปลายทาง / "
        "รายการที่ไม่ใช่การโอน: ส่วนงานบนหัวเอกสาร",
    )
    amount = fields.Float(string="จำนวนเงิน", digits="Product Price", readonly=True)
    status = fields.Selection(
        [
            ("received", "ได้รับแล้ว"),
            ("in_progress", "อยู่ระหว่างดำเนินการ"),
            ("off_target", "พิกัดไม่ตรงกับโครงการ"),
        ],
        string="สถานะ",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW kmitl_project_funding AS (
                SELECT
                    l.id AS id,
                    p.id AS project_id,
                    p.company_id AS company_id,
                    COALESCE(t.name, m.name) AS name,
                    m.date AS date,
                    l.transfer_direction AS direction,
                    l.account_id AS account_id,
                    CASE
                        WHEN t.id IS NULL THEN m.department_analytic_id
                        ELSE (
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
                        WHEN NOT COALESCE(
                            l.account_id = p.budget_account_id
                            AND l.account_fiscal_year_id = p.account_fiscal_year_id
                            AND l.company_id = p.company_id
                            AND p.analytic_distribution
                                ? l.department_analytic_id::text
                            AND p.analytic_distribution ? l.source_analytic_id::text
                            AND p.analytic_distribution ? l.fund_analytic_id::text
                            AND p.analytic_distribution
                                ? l.activity_analytic_id::text,
                            FALSE
                        ) THEN 'off_target'
                        WHEN m.state = 'posted' THEN 'received'
                        ELSE 'in_progress'
                    END AS status
                FROM budget_move_line l
                JOIN budget_move m ON m.id = l.move_id
                JOIN kmitl_project p
                    ON p.analytic_account_id = l.kmitl_project_analytic_id
                LEFT JOIN budget_transfer t ON t.move_id = m.id
                WHERE m.active
                    AND m.move_type IN ('appropriation', 'entry')
                    AND (
                        m.state = 'posted'
                        OR t.state IN ('submitted', 'sent', 'returned')
                    )
            )
            """
        )
