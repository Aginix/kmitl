import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    kid = fields.Char(
        string="KID",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )

    _sql_constraints = [("unique_kid", "unique(kid)", "KID already exists!")]

    def init(self):
        super().init()
        # When this module is installed on a table that already holds employees
        # (e.g. Odoo demo employees), the new required ``kid`` column is filled
        # with the same default placeholder on every existing row. That would
        # violate the ``unique(kid)`` constraint, which is added right after
        # this method. Give each conflicting/empty row a unique KID first. This
        # is a no-op on upgrades, where existing rows already hold unique KIDs.
        self.env.cr.execute(
            """
            WITH conflicting AS (
                SELECT id, row_number() OVER (ORDER BY id) AS rn
                FROM hr_employee
                WHERE kid IS NULL
                   OR kid IN (
                       SELECT kid FROM hr_employee
                       WHERE kid IS NOT NULL
                       GROUP BY kid HAVING count(*) > 1
                   )
            )
            UPDATE hr_employee e
            SET kid = 'K' || lpad(c.rn::text, 5, '0')
            FROM conflicting c
            WHERE e.id = c.id
            """
        )

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val["kid"] = self.env["ir.sequence"].next_by_code("hr.employee.kmitl.kid")
        result = super(__class__, self).create(vals)
        return result
