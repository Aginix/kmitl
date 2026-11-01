from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WorkCenterRoute(models.Model):
    """The standard route of a document model: the ordered chain of stations
    its documents normally pass through. It is configuration, read live — it is
    not copied onto a document, so editing it moves documents in flight too.
    """

    _name = "work.center.route"
    _description = "Standard Route"
    _order = "id"

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
    area_model_ids = fields.Many2many(related="area_id.model_ids")
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="work.center.route.line",
        inverse_name="route_id",
        string="Stations on the Route",
    )

    @api.constrains("area_id", "model_id", "active")
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
            if route.active and self.search_count(
                [
                    ("id", "!=", route.id),
                    ("model_id", "=", route.model_id.id),
                    ("active", "=", True),
                ]
            ):
                raise ValidationError(
                    _("%s already has an active route.") % route.model_id.name
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
