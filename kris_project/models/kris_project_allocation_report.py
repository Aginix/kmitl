from odoo import fields, models, tools


class KrisProjectAllocationReport(models.Model):
    _name = "kris.project.allocation.report"
    _description = "KRIS Project Allocation Analysis"
    _auto = False
    _rec_name = "project_id"
    _order = "project_id desc, id desc"

    # --- Dimensions ---
    allocation_line_id = fields.Many2one(
        "kris.project.allocation.line", string="Allocation", readonly=True
    )
    project_id = fields.Many2one("kris.project", string="Project ID", readonly=True)
    project_name = fields.Char(string="Project Name", readonly=True)
    item_id = fields.Many2one(
        "kris.project.allocation.item", string="Allocator", readonly=True
    )
    name = fields.Char(string="Allocator", readonly=True)
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
    # Allocation lines carry their own department (distinct from the project's)
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
    estimated_amount = fields.Monetary(string="Estimated Amount (Baht)", readonly=True)
    actual_amount = fields.Monetary(string="Actual Amount (Baht)", readonly=True)
    allocation_pct = fields.Float(
        string="Allocation %", digits=(5, 2), readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    a.id                                                   AS id,
                    a.id                                                   AS allocation_line_id,
                    a.project_id                                           AS project_id,
                    p.project_name                                         AS project_name,
                    a.item_id                                              AS item_id,
                    a.name                                                 AS name,
                    p.state                                                AS project_state,
                    p.project_category_id                                  AS project_category_id,
                    p.project_type_id                                      AS project_type_id,
                    p.manager_id                                           AS manager_id,
                    p.user_id                                              AS user_id,
                    p.account_fiscal_year_id                               AS account_fiscal_year_id,
                    p.company_id                                           AS company_id,
                    c.currency_id                                          AS currency_id,
                    a.department_analytic_id                               AS department_analytic_id,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 1), '')::integer AS department_analytic_id_lvl1,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 2), '')::integer AS department_analytic_id_lvl2,
                    NULLIF(SPLIT_PART(d.parent_path, '/', 3), '')::integer AS department_analytic_id_lvl3,
                    a.estimated_amount                                     AS estimated_amount,
                    a.actual_amount                                        AS actual_amount,
                    a.allocation_pct                                       AS allocation_pct
                FROM kris_project_allocation_line a
                JOIN kris_project p ON p.id = a.project_id
                JOIN res_company c ON c.id = p.company_id
                LEFT JOIN account_analytic_account d ON d.id = a.department_analytic_id
            )
        """
            % self._table
        )
