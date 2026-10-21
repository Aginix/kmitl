from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import datetime, safe_eval, time


class PurchaseBuddy(models.Model):
    """One coverage row: a Buddy (central procurement officer) looks after
    the documents of one model that match a domain — typically a requesting
    unit (ส่วนงานผู้ขอ) and its sub-units, e.g.
    ``[('requesting_department_id', 'child_of', 42)]``, optionally narrowed
    further. A document may have several buddies and a buddy may hold several
    rows."""

    _name = "purchase.buddy"
    _description = "Purchase Buddy Coverage"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Buddy",
        required=True,
        index=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_buddy.group_purchase_buddy").ids,
            )
        ],
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(related="model_id.model")
    domain = fields.Char(default="[]", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.domain = "[]"

    @api.constrains("model_id", "domain")
    def _check_model_domain(self):
        for row in self:
            try:
                expression.expression(row._get_domain(), self.env[row.model_id.model])
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

    @api.model
    def _get_buddy_users(self, record):
        """Return the active buddies whose rows match ``record``, ordered by
        ``sequence`` (primary first). Rows of another company, and users
        who have since left the Buddy group, are ignored."""
        domain = [
            ("active", "=", True),
            ("user_id.active", "=", True),
            (
                "user_id.groups_id",
                "in",
                self.env.ref("purchase_buddy.group_purchase_buddy").ids,
            ),
            ("model_id.model", "=", record._name),
        ]
        if "company_id" in record._fields and record.company_id:
            domain.append(("company_id", "=", record.company_id.id))
        rows = self.sudo().search(domain)
        record = record.sudo()
        rows = rows.filtered(
            lambda r: record.filtered_domain(r._resolve_hierarchy(r._get_domain()))
        )
        return rows.mapped("user_id").sudo(False)

    def _resolve_hierarchy(self, domain):
        """Rewrite ``child_of``/``parent_of`` leaves as plain ``in`` leaves.

        ``filtered_domain`` evaluates those operators with a database search
        on the record's ids, so they never match an unsaved record (a form's
        onchange) and read the stored values instead of the form's."""
        self.ensure_one()
        result = []
        for leaf in domain:
            if expression.is_leaf(leaf) and leaf[1] in ("child_of", "parent_of"):
                path, operator, value = leaf
                comodel = self.env[self.model_id.model]
                for fname in path.split("."):
                    if fname != "id":
                        comodel = self.env[comodel._fields[fname].comodel_name]
                leaf = (path, "in", comodel.search([("id", operator, value)]).ids)
            result.append(leaf)
        return result
