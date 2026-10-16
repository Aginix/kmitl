from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import datetime, safe_eval, time


class BudgetBuddy(models.Model):
    """One coverage row: a Buddy (central-office officer) looks after a unit
    (ส่วนงาน). A unit may have several buddies and a buddy may cover several
    units; coverage on a parent unit extends to all of its sub-units.

    A row may be narrowed to one document model and a domain on it (e.g. only
    transfers above a threshold). Without a model it covers every document of
    the unit."""

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
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        ondelete="cascade",
        domain=[("field_id.name", "=", "department_analytic_id")],
        help="Empty: the row covers every document of the unit. Set: it covers "
        "only documents of this model that match the domain.",
    )
    model_name = fields.Char(related="model_id.model")
    domain = fields.Char(default="[]", required=True)
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

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.domain = "[]"

    @api.constrains("model_id", "domain")
    def _check_model_domain(self):
        for row in self.filtered("model_id"):
            Model = self.env[row.model_id.model]
            if "department_analytic_id" not in Model._fields:
                raise ValidationError(
                    _("%s has no unit (ส่วนงาน) to match.") % row.model_id.name
                )
            try:
                expression.expression(row._get_domain(), Model)
            except Exception as e:
                raise ValidationError(_("Invalid domain: %s") % e) from e

    def _get_domain(self):
        self.ensure_one()
        return safe_eval(
            self.domain or "[]",
            {
                "uid": self.env.uid,
                "user": self.env.user,
                "datetime": datetime,
                "time": time,
                "relativedelta": relativedelta,
                "context_today": lambda: fields.Date.context_today(self),
            },
        )

    def _covers(self, record):
        """Whether this row covers ``record`` (rows without a model cover any)."""
        self.ensure_one()
        if not self.model_id:
            return True
        return (
            record is not None
            and record._name == self.model_id.model
            and bool(record.sudo().filtered_domain(self._get_domain()))
        )

    @api.model
    def _get_buddy_users(self, department, record=None):
        """Return the active buddies covering ``department``, primary first.

        A row on any ancestor of the department covers it (parent_path). The
        most specific unit wins — a sub-unit's own buddy ranks before its
        parent's — then ``sequence``. Rows narrowed to a model/domain count
        only when ``record`` (a document of that model) matches.
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
        rows = rows.filtered(lambda r: r._covers(record)).sorted(
            lambda r: (-depth[r.department_analytic_id.id], r.sequence, r.id)
        )
        return rows.mapped("user_id").sudo(False)
