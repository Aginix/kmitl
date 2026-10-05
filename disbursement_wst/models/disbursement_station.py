# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementStation(models.Model):
    """A work station a signed disbursement request passes through.

    Each station is declared by its own ``disbursement_wst_<station>`` module;
    this engine only defines what a station is. Ordering constraints between
    stations are declared as codes (``requires_codes``), never as xmlids, so a
    station that is not installed simply imposes no constraint (ADR-0002).
    """

    _name = "disbursement.station"
    _description = "Disbursement Work Station"
    _order = "sequence, id"

    code = fields.Char(required=True, copy=False)
    name = fields.Char(required=True, translate=True)
    group_id = fields.Many2one(
        "res.groups",
        string="Authorised Group",
        required=True,
        help="Only members of this group may act on the station's step.",
    )
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Todo Type",
        help="Todo pushed to every member of the group when the request "
        "reaches this station.",
    )
    is_signature = fields.Boolean(
        string="Prints a Signature",
        help="Show the actor's frozen signature in the printed request.",
    )
    requires_codes = fields.Char(
        string="Must Come After",
        readonly=True,
        help="Comma-separated codes of stations that must precede this one in "
        "any route that contains them. Declared by code, not editable.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The station code must be unique."),
    ]

    def _required_codes(self):
        self.ensure_one()
        return [
            code.strip()
            for code in (self.requires_codes or "").split(",")
            if code.strip()
        ]
