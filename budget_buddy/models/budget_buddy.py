from odoo import api, fields, models


class BudgetBuddy(models.Model):
    """One coverage row: a Buddy (central-office officer) looks after a unit
    (ส่วนงาน). A unit may have several buddies and a buddy may cover several
    units; coverage on a parent unit extends to all of its sub-units."""

    _name = "budget.buddy"
    _description = "Budget Buddy Coverage"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Buddy",
        required=True,
        index=True,
        domain=lambda self: [
            ("groups_id", "in", self.env.ref("budget_buddy.group_budget_buddy").ids)
        ],
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ส่วนงาน",
        required=True,
        index=True,
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "user_department_uniq",
            "unique(user_id, department_analytic_id)",
            "This buddy already covers this unit.",
        ),
    ]

    @api.model
    def _get_buddy_users(self, department):
        """Return the active buddies covering ``department``, primary first.

        A row on any ancestor of the department covers it (parent_path). The
        most specific unit wins — a sub-unit's own buddy ranks before its
        parent's — then ``sequence``.
        """
        if not department:
            return self.env["res.users"]
        ancestor_ids = [int(i) for i in department.parent_path.strip("/").split("/")]
        rows = self.sudo().search(
            [
                ("active", "=", True),
                ("user_id.active", "=", True),
                ("department_analytic_id", "in", ancestor_ids),
            ]
        )
        depth = {aid: level for level, aid in enumerate(ancestor_ids)}
        rows = rows.sorted(
            lambda r: (-depth[r.department_analytic_id.id], r.sequence, r.id)
        )
        return rows.mapped("user_id").sudo(False)
