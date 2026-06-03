import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .budget_tree import BudgetTree

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    """
    Budget Account - Chart of accounts structure for budget management.

    Business Purpose:
        Defines the budget chart of accounts with hierarchical structure,
        supporting both revenue and expense budget categories aligned with
        Thai government accounting standards.

    Key Features:
        • Hierarchical account structure with parent-child relationships
        • Revenue/Expense budget type classification
        • Fund-specific account restrictions for validation
        • Integration with Thai government chart of accounts
        • Sequence-based ordering for reporting consistency

    Account Types:
        • **Revenue Accounts**: Income and funding sources
        • **Expense Accounts**: Operational and capital expenditures

    Thai Government Integration:
        • Aligned with Thai government accounting codes
        • Support for government budget classification standards
        • Compatible with ministry and university accounting structures
    """

    _name = "budget.account"
    _description = "Budget Account"
    _parent_store = True
    _order = "code"
    _rec_names_search = ["name", "code"]

    _inherit = ["mail.thread"]

    def _default_sequence(self):
        """
        TODO: จะต้องแก้ให้ดึงค่า sequence จากเฉพาะกลุ่ม parent_id ของตัวเองเท่านั้น
        """
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    code = fields.Char("รหัสงบประมาณ", required=True, tracking=True, copy=False)
    name = fields.Char("ชื่อรายการ", required=True, tracking=True, copy=False)
    sequence = fields.Integer(default=_default_sequence)
    complete_name = fields.Char(
        compute="_compute_complete_name", recursive=True, store=True
    )
    note = fields.Text("Internal Notes", tracking=True)
    parent_id = fields.Many2one(
        "budget.account",
        string="Parent",
        index=True,
        ondelete="cascade",
        domain="[('budget_type', '=', budget_type)]",
        copy=True,
        tracking=True,
    )
    child_ids = fields.One2many("budget.account", "parent_id", string="Childs")
    parent_path = fields.Char(index=True, unaccent=False)
    budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        required=True,
        copy=True,
        default="expense",
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
        domain=[("root_plan_id.code", "=", "funds")],
        copy=True,
        tracking=True,
    )

    budgetable = fields.Boolean(
        string="ระบุงบประมาณได้",
        help="ติ๊กถูกเพื่อระบุว่ารหัสค่าใช้จ่ายสามารถจัดสรรงบประมาณได้",
        default=True,
        copy=True,
        tracking=True,
    )

    cross_chargeable = fields.Boolean(
        string="ถัวจ่ายได้",
        help=(
            "ติ๊กถูกเพื่ออนุญาตให้รหัสนี้ถัวจ่ายร่วมกับรหัสอื่นในใบจองเดียวได้ "
            "ใบจองจะมีหลายรหัสได้ก็ต่อเมื่อทุกรหัสติ๊กถัวจ่ายได้ด้วยกัน"
        ),
        default=False,
        copy=True,
        tracking=True,
    )

    children_count = fields.Integer(
        "Children Accounts Count",
        compute="_compute_children_count",
    )

    deprecated = fields.Boolean(
        default=False,
        tracking=True,
        help=(
            "Set deprecated to true to mark the Budget Account that has "
            "been outdated, that you should no longer use it."
        ),
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="Set active to false to hide the Budget Account without removing it.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    is_asset = fields.Boolean(
        string="Is Asset",
        compute="_compute_is_asset",
        store=True,
        recursive=True,
    )
    _sql_constraints = [
        (
            "unique_budget_account_line",
            "unique (code)",
            _("Budget Account must be unique"),
        )
    ]

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault("code", _("%s (copy)", self.code))
        default.setdefault("name", _("%s (copy)", self.name))
        return super().copy_data(default)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = _("%(parent)s / %(own)s") % {
                    "parent": record.parent_id.complete_name,
                    "own": record.name,
                }
            else:
                record.complete_name = record.name

    @api.depends("child_ids")
    def _compute_children_count(self):
        for record in self:
            record.children_count = len(record.child_ids)

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for record in self:
            if record.parent_id:
                record.hierarchy_level = record.parent_id.hierarchy_level + 1
            else:
                record.hierarchy_level = 0

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create recursive budget account."))

    def name_get(self):
        res = []
        for record in self:
            name = record.complete_name
            if record.code:
                name = f"[{record.code}] {name}"
            if record.parent_id:
                name = _("%(name)s") % {
                    "name": name,
                }
            res.append((record.id, name))
        return res

    def action_view_children_accounts(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "budget.account",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id},
            "name": _("Budget Accounts"),
            "view_mode": "list,form",
        }
        return result

    @api.model
    def get_as_tree(self, domain=None):
        if domain is None:
            domain = []
        accounts = self.env["budget.account"].search(domain, order="code")
        nodes = {item.id: BudgetTree.create_node(item) for item in accounts}

        tree = []
        for item in nodes.values():
            if item.parent_id and item.parent_id in nodes and item.parent_id != item.id:
                nodes[item.parent_id].add_child(item)
                item.parent = nodes[item.parent_id]
            else:
                tree.append(item)

        return tree

    def write(self, vals):
        if "budget_type" in vals:
            for account in self:
                if vals.get("budget_type") != account.budget_type:
                    raise UserError(_("You cannot change the budget type."))
        return super().write(vals)

    @api.depends("code", "parent_id", "parent_id.is_asset")
    def _compute_is_asset(self):
        asset_code = "5412000000"

        for record in self:
            is_asset = False

            if record.code and record.code.startswith(asset_code):
                is_asset = True
            elif record.parent_id:
                is_asset = record.parent_id.is_asset

            record.is_asset = is_asset
