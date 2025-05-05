import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetTemplate(models.Model):
    _name = "budget.template"
    _description = "Budget Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(tracking=True)
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        search="_search_date_range_fy",
        tracking=True,
    )
    note = fields.Text("Internal Notes", tracking=True)
    budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        required=True,
        default="expense",
    )
    line_ids = fields.One2many(
        comodel_name="budget.template.line",
        inverse_name="template_id",
        copy=True,
        tracking=True,
    )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain


class BudgetTemplateLine(models.Model):
    _name = "budget.template.line"
    _description = "Budget Template Lines"
    _parent_store = True
    _order = "sequence"
    _inherit = ["mail.thread"]

    template_id = fields.Many2one(
        comodel_name="budget.template",
        index=True,
        ondelete="cascade",
        readonly=True,
        copy=True,
    )

    def _default_sequence(self):
        """
        TODO: จะต้องแก้ให้ดึงค่า sequence จากเฉพาะกลุ่ม parent_id ของตัวเองเท่านั้น
        """
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    code = fields.Char("รหัสงบประมาณ", required=True, tracking=True, copy=True)
    name = fields.Char("ชื่อรายการ", required=True, tracking=True, copy=True)
    sequence = fields.Integer(default=_default_sequence)

    def name_get(self):
        return [(record.id, "%s %s" % (record.code, record.name)) for record in self]

    parent_id = fields.Many2one(
        "budget.template.line",
        string="Parent",
        index=True,
        ondelete="cascade",
        copy=True,
    )
    child_ids = fields.One2many("budget.template.line", "parent_id", string="Childs")
    parent_path = fields.Char(index=True, unaccent=False)
    budget_type = fields.Selection(
        related="template_id.budget_type",
        readonly=True,
        store=True,
        copy=True,
    )

    account_ids = fields.One2many(
        "budget.template.line.account",
        "budget_template_line_id",
        string="Account Mapping",
        copy=True,
        required=False,
    )

    hierarchy_level = fields.Integer(
        string="Level",
        compute="_compute_hierarchy_level",
        store=False,
        recursive=True,
    )

    fund_analytic_ids = fields.Many2many(
        "account.analytic.account",
        string="กองทุน",
        help="ผูกรหัสงบประมาณกับกองทุน",
        ondelete="restrict",
    )

    _sql_constraints = [
        (
            "unique_budget_template_line",
            "unique (template_id, code)",
            _("Budget indicator must be unique"),
        )
    ]

    @api.model
    def create(self, vals):
        record = super(BudgetTemplateLine, self).create(vals)
        return record

    def write(self, vals):
        res = super(BudgetTemplateLine, self).write(vals)
        if "fund_analytic_ids" in vals:
            for record in self:
                if record.child_ids:
                    record.child_ids.write(
                        {"fund_analytic_ids": [(6, 0, record.fund_analytic_ids.ids)]}
                    )
        # ถ้ามี parent_id และ fund_analytic_ids ว่าง ให้ใช้ค่าจาก parent
        for record in self:
            if record.parent_id and not record.fund_analytic_ids:
                record.write({
                    "fund_analytic_ids": [(6, 0, record.parent_id.fund_analytic_ids.ids)]
                })
        return res

    @api.depends("parent_id", "parent_id.fund_analytic_ids")
    def _compute_fund_accounts(self):
        # ถ้ามี parent ให้ใช้ค่า fund_analytic_ids จาก parent
        for record in self:
            if record.parent_id:
                record.fund_analytic_ids = record.parent_id.fund_analytic_ids
            # ถ้าไม่มี parent ให้คงค่าเดิม (หรือกำหนดค่าเริ่มต้นถ้าต้องการ)

    @api.onchange("fund_analytic_ids")
    def _onchange_fund_analytic_ids(self):
        # เมื่อเปลี่ยนแปลง fund_analytic_ids ใน parent อัปเดตไปยัง child_ids
        _logger.info("Onchange triggered for analytic_account_ids:")
        _logger.info(self.fund_analytic_ids.ids)
        if self.child_ids:
            self.child_ids.write(
                {"fund_analytic_ids": [(6, 0, self.fund_analytic_ids.ids)]}
            )

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.hierarchy_level = report_line.parent_id.hierarchy_level + 1
            else:
                report_line.hierarchy_level = 0

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _("You cannot create recursive budget template line.")
            )

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        if args is None:
            args = []
        domain = ["|", ("code", operator, name), ("name", operator, name)]
        return self.search(domain + args, limit=limit).name_get()

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if domain is None:
            domain = []
        if not fields:
            fields = []
        if "code" not in fields:
            fields.append("code")
        if "name" not in fields:
            fields.append("name")
        return super(BudgetTemplateLine, self).search_read(
            domain, fields, offset, limit, order
        )


class BudgetTemplateLineAccount(models.Model):
    _name = "budget.template.line.account"

    budget_template_line_id = fields.Many2one(
        "budget.template.line",
        ondelete="cascade",
        required=True,
        copy=True,
    )

    account_id = fields.Many2one(
        "account.account",
        ondelete="cascade",
        required=True,
        copy=True,
    )

    line_type = fields.Selection(
        [("balance", "Balance"), ("debit", "Debit"), ("credit", "Credit")],
        required=True,
        copy=True,
        default="balance",
    )

    _sql_constraints = [
        (
            "unique_budget_template_line_account",
            "unique (budget_template_line_id, account_id)",
            _("Account must be unique"),
        )
    ]
