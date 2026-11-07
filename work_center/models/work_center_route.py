from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

from .work_center_rule import eval_domain


class WorkCenterRoute(models.Model):
    """The standard route of a document model: the ordered chain of stations
    its documents normally pass through. It is configuration, read live — it is
    not copied onto a document, so editing it moves documents in flight too.

    A model may have several routes: a document takes the first, in sequence,
    whose condition it matches; the one route without a condition is the
    default.
    """

    _name = "work.center.route"
    _description = "Standard Route"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
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
        index=True,
        ondelete="cascade",
        domain="[('id', 'in', area_model_ids)]",
    )
    model_name = fields.Char(related="model_id.model", string="Model Name")
    area_model_ids = fields.Many2many(related="area_id.model_ids")
    sequence = fields.Integer(default=10)
    domain = fields.Char(string="Condition", default="[]", required=True)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="work.center.route.line",
        inverse_name="route_id",
        string="Stations on the Route",
    )

    def _is_default(self):
        return not eval_domain(self.env, self.domain)

    @api.constrains("area_id", "model_id", "active", "domain")
    def _check_route(self):
        for route in self:
            if route.model_id not in route.area_id.sudo().model_ids:
                raise ValidationError(
                    _("%(model)s is not a document model of work area %(area)s.")
                    % {"model": route.model_id.name, "area": route.area_id.name}
                )
            if route.model_id.model not in self.env or not issubclass(
                type(self.env[route.model_id.model]), self.pool["work.center.mixin"]
            ):
                raise ValidationError(
                    _("%s does not support stations.") % route.model_id.name
                )
            try:
                expression.expression(
                    eval_domain(self.env, route.domain), self.env[route.model_id.model]
                )
            except Exception as e:
                raise ValidationError(
                    _("Invalid condition on route %(route)s: %(error)s")
                    % {"route": route.name, "error": e}
                ) from e
            if (
                route.active
                and route._is_default()
                and self.search(
                    [
                        ("id", "!=", route.id),
                        ("model_id", "=", route.model_id.id),
                        ("active", "=", True),
                    ]
                ).filtered(lambda r: r._is_default())
            ):
                raise ValidationError(
                    _("%s already has an active route without a condition.")
                    % route.model_id.name
                )


class WorkCenterRouteLine(models.Model):
    """One position on a route. Several candidate stations may share it (one
    per ส่วนงาน, say): the routing rules pick which of them takes the document.
    """

    _name = "work.center.route.line"
    _description = "Route Line"
    _order = "sequence, id"

    route_id = fields.Many2one(
        comodel_name="work.center.route",
        required=True,
        index=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    work_center_ids = fields.Many2many(
        comodel_name="work.center",
        relation="work_center_route_line_station_rel",
        column1="line_id",
        column2="work_center_id",
        string="Candidate Stations",
        help="The stations that can take the document at this position. When "
        "there are several, the routing rules choose.",
    )

    @api.constrains("route_id", "work_center_ids")
    def _check_candidates(self):
        for line in self:
            area = line.route_id.area_id
            for station in line.work_center_ids:
                if station.is_unassigned or station.area_id != area:
                    raise ValidationError(
                        _(
                            "%(station)s cannot be on this route: it is the "
                            "Unassigned card or belongs to another work area."
                        )
                        % {"station": station.display_name}
                    )
            others = line.route_id.line_ids - line
            clash = line.work_center_ids & others.work_center_ids
            if clash:
                raise ValidationError(
                    _("%s is already on this route.") % clash[0].display_name
                )
