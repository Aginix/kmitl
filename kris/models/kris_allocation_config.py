# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KrisAllocationConfig(models.Model):
    _name = "kris.allocation.config"
    _description = "KRIS Allocation Configuration"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        comodel_name="kris.allocation.config.line",
        inverse_name="config_id",
        string="Allocation Lines",
        copy=True,
    )
    total_percentage = fields.Float(
        string="Total Percentage",
        compute="_compute_total_percentage",
        store=True,
    )

    @api.depends("line_ids.percentage")
    def _compute_total_percentage(self):
        for config in self:
            config.total_percentage = sum(config.line_ids.mapped("percentage"))

    @api.constrains("line_ids")
    def _check_total_percentage(self):
        for config in self:
            if config.line_ids and abs(config.total_percentage - 100.0) > 0.001:
                raise ValidationError(
                    _(
                        "Allocation lines must sum to 100%%. Current total: %(total).2f%%"
                    )
                    % {"total": config.total_percentage}
                )


class KrisAllocationConfigLine(models.Model):
    _name = "kris.allocation.config.line"
    _description = "KRIS Allocation Configuration Line"
    _order = "sequence, id"

    config_id = fields.Many2one(
        comodel_name="kris.allocation.config",
        string="Configuration",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Label", required=True)
    is_home_department = fields.Boolean(
        string="Home Department",
        help="If enabled, use the project's home department instead of a fixed department.",
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Account",
        required=True,
    )
    percentage = fields.Float(string="Percentage (%)", required=True)

    @api.constrains("percentage")
    def _check_percentage_positive(self):
        for line in self:
            if line.percentage <= 0:
                raise ValidationError(_("Percentage must be positive."))

    @api.constrains("is_home_department", "department_analytic_id")
    def _check_department_required(self):
        for line in self:
            if not line.is_home_department and not line.department_analytic_id:
                raise ValidationError(
                    _(
                        "Department is required when 'Home Department' is not enabled (line: %(name)s)."
                    )
                    % {"name": line.name}
                )
