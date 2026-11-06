from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

from .work_center_rule import eval_domain


class WorkCenterAssignmentRule(models.Model):
    """Assignment rule: chooses which person of a station takes a document
    that arrives there, so the others need not look at it. A document of
    ``model_id`` matching ``domain`` goes to ``user_id``. The rules of one
    station are tried in order; the first match whose person is still
    responsible at the station wins. Without a rule that matches, nobody is
    assigned and the station works as before."""

    _name = "work.center.assignment.rule"
    _description = "Station Assignment Rule"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    work_center_id = fields.Many2one(
        comodel_name="work.center",
        string="Station",
        required=True,
        index=True,
        ondelete="cascade",
        domain="[('is_unassigned', '=', False)]",
    )
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
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assignee",
        required=True,
        ondelete="cascade",
        domain="[('share', '=', False)]",
    )

    @api.constrains("work_center_id", "model_id", "domain")
    def _check_rule(self):
        for rule in self:
            wc = rule.work_center_id
            if wc.is_unassigned:
                raise ValidationError(
                    _("A rule cannot assign on the Unassigned card.")
                )
            if rule.model_id not in wc.area_id.model_ids:
                raise ValidationError(
                    _("%(model)s is not a document model of work area %(area)s.")
                    % {"model": rule.model_id.name, "area": wc.area_id.name}
                )
            if rule.model_name not in self.env:
                raise ValidationError(
                    _("Model %s is not installed.") % rule.model_id.name
                )
            Model = self.env[rule.model_name]
            if not issubclass(type(Model), self.pool["work.center.mixin"]):
                raise ValidationError(
                    _("%s does not support stations.") % rule.model_id.name
                )
            try:
                expression.expression(eval_domain(self.env, rule.domain), Model)
            except Exception as e:
                raise ValidationError(
                    _("Invalid domain on assignment rule of %(wc)s: %(error)s")
                    % {"wc": wc.display_name, "error": e}
                ) from e

    @api.model
    def _match(self, record, station):
        """The person of the first rule of ``station`` matching ``record``
        whose person is still responsible there, or an empty recordset. The
        domain is read the way routing rules are, so ``child_of`` also covers
        the children and works on fields that are not stored."""
        users = station.sudo()._responsible_users()[0]
        record = record.sudo()
        for rule in station.sudo().assignment_rule_ids:
            if rule.model_name != record._name or rule.user_id not in users:
                continue
            domain = self.env["work.center.rule"]._normalize_hierarchy(
                record, eval_domain(self.env, rule.domain)
            )
            if record.filtered_domain(domain):
                return rule.user_id
        return self.env["res.users"]
