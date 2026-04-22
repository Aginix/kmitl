# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.osv import expression


class PaymentCycle(models.Model):
    _name = "payment.cycle"
    _description = "Payment Cycle"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Number",
        readonly=True,
        copy=False,
        default="/",
    )
    description = fields.Char(
        string="Description",
    )
    date = fields.Date(
        string="Planned Payment Date",
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "payment.cycle",
                        sequence_date=vals.get("date"),
                    )
                    or "/"
                )
        return super().create(vals_list)

    @api.depends("date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.date)
            company = rec.company_id
            rec.account_fiscal_year_id = (
                company and date and company.find_daterange_fy(date) or False
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
