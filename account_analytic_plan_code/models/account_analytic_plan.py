import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountAnalyticPlan(models.Model):
    _name = "account.analytic.plan"
    _inherit = ["account.analytic.plan", "mail.activity.mixin"]

    code = fields.Char(tracking=True)  # For internal identification

    _sql_constraints = [
        ("code_unique", "unique (code)", _("The analytic plan code already exists!")),
    ]
