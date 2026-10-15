from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import datetime, safe_eval, time


def eval_domain(env, domain):
    """Evaluate a stored domain string the way search filters do."""
    return safe_eval(
        domain or "[]",
        {
            "uid": env.uid,
            "user": env.user,
            "datetime": datetime,
            "time": time,
            "relativedelta": relativedelta,
            "context_today": lambda: fields.Date.context_today(env.user),
        },
    )


class WorkCenterRule(models.Model):
    """Routing rule: a document of ``model_id`` matching ``domain`` belongs to
    ``work_center_id``. Rules of one model form a single ordered list across all
    work centers; the first match (by sequence) wins. A หน่วยงาน-level work
    center implicitly adds ``operating_unit = its OU`` to its rules."""

    _name = "work.center.rule"
    _description = "Work Center Routing Rule"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    work_center_id = fields.Many2one(
        comodel_name="work.center",
        required=True,
        index=True,
        ondelete="cascade",
        domain="[('is_unassigned', '=', False)]",
    )
    area_id = fields.Many2one(related="work_center_id.area_id")
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        required=True,
        ondelete="cascade",
        domain="[('id', 'in', area_model_ids)]",
    )
    area_model_ids = fields.Many2many(related="work_center_id.area_id.model_ids")
    model_name = fields.Char(related="model_id.model", store=True, index=True)
    domain = fields.Char(default="[]", required=True)

    @api.constrains("work_center_id", "model_id", "domain")
    def _check_rule(self):
        for rule in self:
            wc = rule.work_center_id
            if wc.is_unassigned:
                raise ValidationError(
                    _("A rule cannot route to the 'ยังไม่มีศูนย์งาน' card.")
                )
            if rule.model_id not in wc.area_id.model_ids:
                raise ValidationError(
                    _("%(model)s is not a document model of work area %(area)s.")
                    % {"model": rule.model_id.name, "area": wc.area_id.name}
                )
            Model = self.env[rule.model_name]
            if not issubclass(type(Model), self.pool["work.center.mixin"]):
                raise ValidationError(
                    _("%s does not support work centers.") % rule.model_id.name
                )
            if (
                wc.operating_unit_id
                and Model._work_center_ou_field not in Model._fields
            ):
                raise ValidationError(
                    _(
                        "%s has no operating unit, so it can only be routed to a "
                        "work center without one (ส่วนกลาง)."
                    )
                    % rule.model_id.name
                )
            try:
                expression.expression(eval_domain(self.env, rule.domain), Model)
            except Exception as e:
                raise ValidationError(
                    _("Invalid domain on rule of %(wc)s: %(error)s")
                    % {"wc": wc.display_name, "error": e}
                ) from e

    @api.model
    def _match(self, record):
        """Return the work center of the first rule matching ``record`` (which
        may be a new, unsaved record), or an empty recordset."""
        rules = self.search(
            [
                ("model_name", "=", record._name),
                ("work_center_id.active", "=", True),
            ]
        )
        for rule in rules:
            if record.filtered_domain(rule._get_match_domain(record)):
                return rule.work_center_id
        return self.env["work.center"]

    def _get_match_domain(self, record):
        self.ensure_one()
        domain = self._normalize_hierarchy(record, eval_domain(self.env, self.domain))
        ou = self.work_center_id.operating_unit_id
        if ou:
            domain = expression.AND(
                [domain, [(record._work_center_ou_field, "=", ou.id)]]
            )
        return domain

    @api.model
    def _normalize_hierarchy(self, record, domain):
        """Rewrite ``child_of`` / ``parent_of`` leaves on a direct relational
        field into ``in [ids]``: ``filtered_domain`` resolves those operators
        with a database search, which ignores unsaved (onchange) values."""
        result = []
        for leaf in domain:
            if (
                isinstance(leaf, (list, tuple))
                and len(leaf) == 3
                and leaf[1] in ("child_of", "parent_of")
                and "." not in leaf[0]
            ):
                field = record._fields.get(leaf[0])
                if field and field.relational:
                    ids = (
                        self.env[field.comodel_name]
                        .sudo()
                        .with_context(active_test=False)
                        .search([("id", leaf[1], leaf[2])])
                        .ids
                    )
                    leaf = (leaf[0], "in", ids)
            result.append(leaf)
        return result
