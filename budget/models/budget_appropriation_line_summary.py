import logging
from psycopg2 import sql

from odoo import tools
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationLineSummary(models.Model):
    _name = "budget.appropriation.line.summary"
    _description = "Budget Appropriation Line Summary"
    _auto = False

    code = fields.Char("Code", readonly=True)
    name = fields.Char("Name", readonly=True)
    template_id = fields.Many2one(
        comodel_name="budget.template",
        readonly=True,
    )
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        readonly=True,
    )
    appropriation_id = fields.Many2one(
        comodel_name="budget.appropriation",
        string="Budget Appropriation",
        readonly=True,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        readonly=True,
        domain=[("root_plan_id.code", "=", "departments")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        readonly=True,
        domain=[("root_plan_id.code", "=", "sources")],
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        readonly=True,
        domain=[("root_plan_id.code", "=", "activities")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        readonly=True,
        domain=[("root_plan_id.code", "=", "funds")],
    )
    parent_id = fields.Many2one(
        "budget.appropriation.line.summary",
        string="Parent",
        readonly=True,
    )
    child_ids = fields.One2many(
        "budget.appropriation.line.summary", "parent_id", string="Childs"
    )
    parent_path = fields.Char()
    sequence = fields.Integer()
    amount = fields.Float(
        readonly=True,
        digits="Budget Precision",
        help="Amount",
    )
    credit = fields.Float(
        compute='_compute_debit_credit_balance',
        digits="Budget Precision",
    )
    debit = fields.Float(
        compute='_compute_debit_credit_balance',
        digits="Budget Precision",
    )

    @api.depends('child_ids.amount')
    def _compute_debit_credit_balance(self):
        for record in self.filtered("child_ids"):


    def init(self):
        query = """
WITH line as (
	select
	    concat(bal.template_line_id, '-',  bal.activity_analytic_id, '-', bal.department_analytic_id, '-', bal.fund_analytic_id, '-', bal.source_analytic_id, '-', bal.appropriation_id, '-', bal.id) as id,
	    btl.code,
	    btl.name,
	    bal.template_id,
	    bal.template_line_id,
	    btl.parent_id,
	    btl.parent_path,
	    btl.sequence,
	    bal.amount,
	    bal.credit,
	    bal.debit,
	    bal.activity_analytic_id,
	    bal.department_analytic_id,
	    bal.fund_analytic_id,
	    bal.source_analytic_id,
	    bal.appropriation_id
	    from budget_appropriation_line bal
	inner join budget_template_line btl
	on bal.template_line_id = btl.id
)
select
		line.id,
		case
		 when line.template_line_id = tl.id then line.code
		 else tl.code
	    end as code,
	    case
		 when line.template_line_id = tl.id then line.name
		 else tl."name"
	    end as name,
	    line.template_id,
	    case
		 when line.template_line_id = tl.id then line.template_line_id
		 else tl.id
	    end as template_line_id,
	    line.parent_id,
	    line.parent_path,
	    line.sequence,
	    case
		 when line.template_line_id = tl.id then line.amount
		 else 0
	    end as amount,
	    case
		 when line.template_line_id = tl.id then line.credit
		 else 0
	    end as credit,
	    case
		 when line.template_line_id = tl.id then line.debit
		 else 0
	    end as debit,
	    line.activity_analytic_id,
	    line.department_analytic_id,
	    line.fund_analytic_id,
	    line.source_analytic_id,
	    line.appropriation_id
from line
left join budget_template_line tl
on
	line.parent_path like concat('%%/', tl.id,'/%%')
	or line.parent_path like concat(tl.id, '/%%')
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table), sql.SQL(query)
            )
        )
