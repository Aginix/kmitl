# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ReceiptKmitlLine(models.Model):
    _name = "kmitl.receipt.line"
    _description = "KMITL Receipt Line"
    _inherit = ["analytic.mixin"]
    _order = "receipt_id, sequence, id"

    receipt_id = fields.Many2one(
        "kmitl.receipt",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain="[('property_account_income_id', '!=', False)]",
    )
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one(
        "account.account",
        string="Income Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'income'),"
               " ('company_id', 'in', allowed_company_ids)]",
    )
    company_id = fields.Many2one(
        related="receipt_id.company_id",
        store=True,
        readonly=True,
    )
    quantity = fields.Float(default=1.0, required=True, digits="Product Unit of Measure")
    price_unit = fields.Monetary(required=True, currency_field="currency_id")
    amount = fields.Monetary(
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="receipt_id.currency_id",
        store=True,
        readonly=True,
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
    )
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="KMITL Project",
        compute="_compute_analytic_id",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Procurement Plan",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "kmitl_project": "kmitl_project_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        for line in self:
            line._update_analytic_distribution("sources")

    def _inverse_kmitl_project_analytic(self):
        for line in self:
            line._update_analytic_distribution("kmitl_project")

    def _inverse_procurement_plan_analytic(self):
        for line in self:
            line._update_analytic_distribution("procurement_plan")

    @api.depends("quantity", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.amount = (line.quantity or 0.0) * (line.price_unit or 0.0)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            product = line.product_id
            if not line.name:
                line.name = product.display_name
            line.account_id = (
                product.property_account_income_id
                or product.categ_id.property_account_income_categ_id
            )
            if not line.price_unit:
                line.price_unit = product.lst_price
