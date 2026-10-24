from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

from .work_center_rule import eval_domain


class WorkCenterCounter(models.Model):
    """A number shown on every station card of an area, e.g. 'เอกสารรอตรวจสอบ'.
    Counts the card's documents of ``model_id`` matching ``domain``; clicking it
    opens that list. Seeded by the bridges, editable by the admin."""

    _name = "work.center.counter"
    _description = "Station Counter"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    area_id = fields.Many2one(
        comodel_name="work.center.area",
        string="Work Area",
        required=True,
        index=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        required=True,
        ondelete="cascade",
        domain="[('id', 'in', area_model_ids)]",
    )
    area_model_ids = fields.Many2many(related="area_id.model_ids")
    model_name = fields.Char(related="model_id.model", store=True)
    domain = fields.Char(default="[]", required=True)

    @api.constrains("area_id", "model_id", "domain")
    def _check_counter(self):
        for counter in self:
            if counter.model_id not in counter.area_id.model_ids:
                raise ValidationError(
                    _("%(model)s is not a document model of work area %(area)s.")
                    % {"model": counter.model_id.name, "area": counter.area_id.name}
                )
            if counter.model_name not in self.env:
                raise ValidationError(
                    _("Model %s is not installed.")
                    % (counter.model_name or counter.model_id.name)
                )
            Model = self.env[counter.model_name]
            try:
                expression.expression(counter._get_domain(), Model)
            except Exception as e:
                raise ValidationError(
                    _("Invalid domain on counter %(name)s: %(error)s")
                    % {"name": counter.name, "error": e}
                ) from e

    def _get_domain(self):
        self.ensure_one()
        return eval_domain(self.env, self.domain)
