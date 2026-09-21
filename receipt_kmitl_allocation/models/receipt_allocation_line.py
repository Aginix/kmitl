# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

# Root plan code → convenience field. Blank = inherit the receipt header's
# value; filled = pin this bucket to a fixed unit.
ANALYTIC_KEYS = {
    "departments": "department_analytic_id",
    "sources": "source_analytic_id",
    "funds": "fund_analytic_id",
    "activities": "activity_analytic_id",
    "kmitl_project": "kmitl_project_analytic_id",
    "procurement_plan": "procurement_plan_analytic_id",
}


class ReceiptAllocationLine(models.Model):
    _name = "receipt.allocation.line"
    _description = "Receipt Revenue Allocation Bucket"
    _inherit = ["analytic.mixin"]
    _order = "product_tmpl_id, sequence, id"
    _analytic_keys = ANALYTIC_KEYS

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="product_tmpl_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="product_tmpl_id.currency_id",
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, help="Bucket label, e.g. ค่าบำรุงสถาบัน")
    account_id = fields.Many2one(
        "account.account",
        string="Revenue Account",
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'income'),"
        " ('company_id', 'in', allowed_company_ids)]",
    )
    method = fields.Selection(
        [("percent", "เปอร์เซ็นต์"), ("fixed", "จำนวนคงที่")],
        required=True,
        default="percent",
    )
    percentage = fields.Float(string="Percentage (%)")
    fixed_amount = fields.Monetary(currency_field="currency_id")

    # --- Analytic dimension overrides (blank = inherit from receipt) ---
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Issuing Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        compute_sudo=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        compute_sudo=True,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        compute_sudo=True,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        compute_sudo=True,
    )
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="KMITL Project",
        compute="_compute_analytic_id",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        compute_sudo=True,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Procurement Plan",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        compute_sudo=True,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        # Reset first: the shared mixin only assigns dimensions present in
        # the JSON, so a removed override would otherwise keep its stale
        # value. Same guard as kmitl.receipt._compute_analytic_id.
        for rec in self:
            for field_name in self._analytic_keys.values():
                rec[field_name] = False
        return super()._compute_analytic_id()

    # Same dual-purpose (onchange + field inverse) pattern as
    # receipt_kmitl.py: each must stay single-field, see that file for why.
    @api.onchange("department_analytic_id")
    def _inverse_department_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("departments")

    @api.onchange("source_analytic_id")
    def _inverse_source_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("sources")

    @api.onchange("fund_analytic_id")
    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    @api.onchange("activity_analytic_id")
    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    @api.onchange("kmitl_project_analytic_id")
    def _inverse_kmitl_project_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("kmitl_project")

    @api.onchange("procurement_plan_analytic_id")
    def _inverse_procurement_plan_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("procurement_plan")

    @api.constrains("product_tmpl_id", "method", "percentage", "account_id")
    def _check_allocation_config(self):
        for product in self.mapped("product_tmpl_id"):
            buckets = product.receipt_allocation_line_ids
            if not buckets:
                continue
            if any(not bucket.account_id for bucket in buckets):
                raise ValidationError(
                    _("Every revenue allocation bucket on product '%s' needs "
                      "a revenue account.") % product.name
                )
            percent_buckets = buckets.filtered(lambda b: b.method == "percent")
            if not percent_buckets:
                raise ValidationError(
                    _("Product '%s' has revenue allocation buckets but none "
                      "of them is a percentage bucket; at least one is "
                      "required.") % product.name
                )
            total = sum(percent_buckets.mapped("percentage"))
            if float_compare(total, 100.0, precision_digits=2) != 0:
                raise ValidationError(
                    _("Product '%(product)s' revenue allocation percentages "
                      "must sum to 100 (currently %(total).2f).")
                    % {"product": product.name, "total": total}
                )
