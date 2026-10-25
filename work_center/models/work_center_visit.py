from odoo import _, api, fields, models
from odoo.exceptions import UserError

# What may still change on a visit, and only while it is open and the engine
# is moving the document (the departure, plus the acts done and skipped).
_VISIT_CLOSABLE_FIELDS = {
    "departure_date",
    "departed_by_id",
    "departure_act",
    "departure_reason",
    "done_act_ids",
    "skipped_act_ids",
    "not_applicable_act_ids",
}


class WorkCenterVisit(models.Model):
    """สมุดเยี่ยม — one row per stay of a document at a station.

    The log is the evidence of custody (disbursement_wc ADR-0001): when the
    document arrived and left, who moved it, by which act, why a required act
    was skipped, and who was responsible on arrival. Rows are append-only. The
    engine is the only writer, always as sudo.
    """

    _name = "work.center.visit"
    _description = "Station Visit"
    _order = "id desc"

    res_model = fields.Char(string="Document Model", required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Document ID",
        model_field="res_model",
        required=True,
        index=True,
    )
    document_display = fields.Char(
        string="Document", compute="_compute_document_display"
    )
    work_center_id = fields.Many2one(
        comodel_name="work.center",
        string="Station",
        required=True,
        index=True,
        ondelete="restrict",
    )
    area_id = fields.Many2one(related="work_center_id.area_id", store=True)
    arrival_date = fields.Datetime(
        string="Arrived", required=True, default=fields.Datetime.now
    )
    arrived_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Arrived By",
        default=lambda self: self.env.user,
    )
    arrival_act = fields.Selection(
        selection=[
            ("enter", "Entered the circuit"),
            ("resubmit", "Resubmitted"),
            ("forward", "Forwarded"),
            ("divert", "Diverted"),
        ],
        string="Arrival",
        required=True,
    )
    departure_date = fields.Datetime(string="Left")
    departed_by_id = fields.Many2one(comodel_name="res.users", string="Left By")
    departure_act = fields.Selection(
        selection=[
            ("forward", "Forwarded"),
            ("divert", "Diverted"),
            ("send_back", "Sent back"),
            ("exit", "Left the last station"),
            ("cancel", "Cancelled"),
        ],
        string="Departure",
    )
    departure_reason = fields.Text(
        string="Reason",
        help="Why a required act was skipped, or why the document was "
        "diverted or sent back.",
    )
    done_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_visit_done_act_rel",
        column1="visit_id",
        column2="act_id",
        string="Done Acts",
        context={"active_test": False},
    )
    skipped_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_visit_skipped_act_rel",
        column1="visit_id",
        column2="act_id",
        string="Skipped Acts",
        context={"active_test": False},
        help="Required acts the document left without, with a reason.",
    )
    not_applicable_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_visit_na_act_rel",
        column1="visit_id",
        column2="act_id",
        string="Not Applicable Acts",
        context={"active_test": False},
        help="Required acts the document declared not applicable to itself.",
    )
    responsible_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="work_center_visit_responsible_rel",
        column1="visit_id",
        column2="user_id",
        string="Responsible on Arrival",
        context={"active_test": False},
        help="Who was responsible when the document arrived, frozen. Who may "
        "act is decided live, so the person who acted can be missing here: "
        "that is evidence the membership changed, not a breach.",
    )
    responsible_source = fields.Selection(
        selection=[
            ("members", "Station members"),
            ("role", "Role holders"),
            ("fallback", "Station administrators"),
        ],
        string="Responsible Source",
    )

    @api.depends("res_model", "res_id")
    def _compute_document_display(self):
        for visit in self:
            record = (
                self.env[visit.res_model].sudo().browse(visit.res_id).exists()
                if visit.res_model in self.env
                else None
            )
            visit.document_display = (
                record.display_name if record else f"{visit.res_model},{visit.res_id}"
            )

    def write(self, vals):
        if (
            not self.env.context.get("work_center_moving")
            or any(visit.departure_date for visit in self)
            or set(vals) - _VISIT_CLOSABLE_FIELDS
        ):
            raise UserError(_("Visit log entries are immutable and cannot be modified."))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("work_center_force_unlink"):
            raise UserError(_("Visit log entries cannot be deleted."))
        return super().unlink()
