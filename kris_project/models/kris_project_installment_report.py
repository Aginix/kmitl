from odoo import fields, models, tools


class KrisProjectInstallmentReport(models.Model):
    _name = "kris.project.installment.report"
    _description = "KRIS Project Installment Analysis"
    _auto = False
    _rec_name = "project_id"
    _order = "due_date desc, id desc"

    # --- Dimensions ---
    installment_id = fields.Many2one(
        "kris.project.installment", string="Installment", readonly=True
    )
    project_id = fields.Many2one(
        "kris.project", string="Project ID", readonly=True
    )
    project_name = fields.Char(string="Project Name", readonly=True)
    due_date = fields.Date(string="Date Due", readonly=True)
    state = fields.Selection(
        selection=[
            ("pending", "รอรับเงิน"),
            ("partial", "รับบางส่วน"),
            ("received", "รับเงินแล้ว"),
        ],
        string="Installment State",
        readonly=True,
    )
    project_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        string="Project State",
        readonly=True,
    )
    project_category_id = fields.Many2one(
        "kris.project.category", string="Project Category", readonly=True
    )
    project_type_id = fields.Many2one(
        "kris.project.type", string="Project Type", readonly=True
    )
    manager_id = fields.Many2one(
        "hr.employee", string="Project Manager", readonly=True
    )
    user_id = fields.Many2one("res.users", string="Responsible", readonly=True)
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year", string="Fiscal Year", readonly=True
    )
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    department_analytic_id = fields.Many2one(
        "account.analytic.account", string="ส่วนงาน", readonly=True
    )
    department_analytic_id_lvl1 = fields.Many2one(
        "account.analytic.account", string="ส่วนงาน Lv.1", readonly=True
    )
    department_analytic_id_lvl2 = fields.Many2one(
        "account.analytic.account", string="ส่วนงาน Lv.2", readonly=True
    )
    department_analytic_id_lvl3 = fields.Many2one(
        "account.analytic.account", string="ส่วนงาน Lv.3", readonly=True
    )

    # --- Measures ---
    amount = fields.Monetary(string="Amount Receive", readonly=True)
    deduction_guarantee = fields.Monetary(string="Guarantee Deduction", readonly=True)
    deduction_advance = fields.Monetary(string="Advance Deduction", readonly=True)
    received_from_employer = fields.Monetary(
        string="Received From Client", readonly=True
    )
    maintenance_fee = fields.Monetary(string="Maintenance Fee", readonly=True)
    extra_deduction = fields.Monetary(string="Extra Deduction", readonly=True)
    extra_income = fields.Monetary(string="Extra Value", readonly=True)
    amount_net = fields.Monetary(string="Net Amount", readonly=True)
    received_total = fields.Monetary(string="Received Total", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    i.id                                                   AS id,
                    i.id                                                   AS installment_id,
                    i.project_id                                           AS project_id,
                    p.project_name                                         AS project_name,
                    i.due_date                                             AS due_date,
                    i.state                                                AS state,
                    p.state                                                AS project_state,
                    p.project_category_id                                  AS project_category_id,
                    p.project_type_id                                      AS project_type_id,
                    p.manager_id                                           AS manager_id,
                    p.user_id                                              AS user_id,
                    p.account_fiscal_year_id                               AS account_fiscal_year_id,
                    p.company_id                                           AS company_id,
                    c.currency_id                                          AS currency_id,
                    p.department_analytic_id                               AS department_analytic_id,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 1), '')::integer AS department_analytic_id_lvl1,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 2), '')::integer AS department_analytic_id_lvl2,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 3), '')::integer AS department_analytic_id_lvl3,
                    i.amount                                               AS amount,
                    i.deduction_guarantee                                  AS deduction_guarantee,
                    i.deduction_advance                                    AS deduction_advance,
                    i.received_from_employer                               AS received_from_employer,
                    i.maintenance_fee                                      AS maintenance_fee,
                    i.extra_deduction                                      AS extra_deduction,
                    i.extra_income                                         AS extra_income,
                    i.amount_net                                           AS amount_net,
                    i.received_total                                       AS received_total
                FROM kris_project_installment i
                JOIN kris_project p ON p.id = i.project_id
                JOIN res_company c ON c.id = p.company_id
                LEFT JOIN account_analytic_account d ON d.id = p.department_analytic_id
            )
        """
            % self._table
        )
