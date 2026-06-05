from odoo import fields, models, tools


class KrisProjectReceiptReport(models.Model):
    _name = "kris.project.receipt.report"
    _description = "KRIS Project Revenue Analysis"
    _auto = False
    _rec_name = "project_id"
    _order = "date desc, id desc"

    # --- Dimensions ---
    receipt_id = fields.Many2one(
        "kris.project.receipt", string="Receipt", readonly=True
    )
    project_id = fields.Many2one("kris.project", string="Project", readonly=True)
    installment_id = fields.Many2one(
        "kris.project.installment", string="Installment Number", readonly=True
    )
    date = fields.Date(string="Receipt Date", readonly=True)
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
    amount = fields.Monetary(string="Amount", readonly=True)
    equipment_cost_in_installment = fields.Monetary(
        string="Equipment Cost in Installment", readonly=True
    )
    extra_income = fields.Monetary(string="Extra Value", readonly=True)
    net_amount = fields.Monetary(string="Net Amount", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    r.id                                                   AS id,
                    r.id                                                   AS receipt_id,
                    r.project_id                                           AS project_id,
                    r.installment_id                                       AS installment_id,
                    r.date                                                 AS date,
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
                    r.amount                                               AS amount,
                    r.equipment_cost_in_installment                        AS equipment_cost_in_installment,
                    r.extra_income                                         AS extra_income,
                    r.net_amount                                           AS net_amount
                FROM kris_project_receipt r
                JOIN kris_project p ON p.id = r.project_id
                JOIN res_company c ON c.id = p.company_id
                LEFT JOIN account_analytic_account d ON d.id = p.department_analytic_id
            )
        """
            % self._table
        )
