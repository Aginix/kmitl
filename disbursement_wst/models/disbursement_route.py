# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class DisbursementRoute(models.Model):
    """The ordered list of stations a request walks through (route template).

    A route is seeded onto a request once, when it is signed; editing a route
    never alters requests already on their way.
    """

    _name = "disbursement.route"
    _description = "Disbursement Route"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10, help="Match priority (lower = first).")
    condition_domain = fields.Char(
        help="Domain on the request that selects this route. Empty = any.",
    )
    request_model = fields.Char(compute="_compute_request_model")
    line_ids = fields.One2many(
        "disbursement.route.line", "route_id", string="Stations", copy=True
    )

    def _compute_request_model(self):
        self.request_model = "disbursement.request"

    @api.constrains("line_ids")
    def _check_station_order(self):
        """A station may not precede a station it declares it must follow.

        Stations not in the route (or not installed) impose nothing.
        """
        for route in self:
            order = {
                line.station_id.code: line.sequence for line in route.line_ids
            }
            for line in route.line_ids:
                for code in line.station_id._required_codes():
                    if code in order and order[code] >= line.sequence:
                        raise ValidationError(
                            _(
                                "Station %(station)s must come after "
                                "station %(required)s.",
                                station=line.station_id.name,
                                required=route.line_ids.filtered(
                                    lambda x, code=code: x.station_id.code == code
                                )[:1].station_id.name,
                            )
                        )

    def _match(self, request):
        self.ensure_one()
        return _domain_matches(self.condition_domain, request)

    @api.model
    def _find_for(self, request):
        """The first active route whose condition matches ``request``."""
        for route in self.search([]):
            if route._match(request):
                return route
        return self.browse()


class DisbursementRouteLine(models.Model):
    _name = "disbursement.route.line"
    _description = "Disbursement Route Line"
    _order = "sequence, id"

    route_id = fields.Many2one(
        "disbursement.route", required=True, ondelete="cascade", index=True
    )
    station_id = fields.Many2one(
        "disbursement.station", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    condition_domain = fields.Char(
        help="The station is skipped when the request does not match. "
        "Empty = always visited.",
    )
    request_model = fields.Char(compute="_compute_request_model")

    def _compute_request_model(self):
        self.request_model = "disbursement.request"


def _domain_matches(domain_str, request):
    """Whether ``request`` satisfies the stored domain (empty = always)."""
    if not domain_str:
        return True
    domain = safe_eval(domain_str, {"uid": request.env.uid})
    return bool(request.filtered_domain(domain))
