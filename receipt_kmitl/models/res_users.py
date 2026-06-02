# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    kmitl_department_ids = fields.Many2many(
        "account.analytic.account",
        "res_users_kmitl_department_rel",
        "user_id",
        "department_id",
        string="KMITL Departments",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Departments this user is allowed to operate on for "
             "KMITL receipts and cash deposits.",
    )
