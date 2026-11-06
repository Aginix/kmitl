from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class WorkCenter(models.Model):
    """สถานี — a desk a document passes through while one step of its handling
    is done (see ADR-0002).

    A document is at one station at a time and the station moves forward along
    a route or is diverted, every move written to the visit log. A station
    lists the acts it allows and requires. Its members narrow who may act: they
    never grant a right the role does not already give. With an operating unit
    the station is หน่วยงาน-level (it only takes documents of that OU); without
    one it is ส่วนกลาง-level.
    """

    _name = "work.center"
    _description = "Station"
    _inherit = ["mail.thread"]
    _order = "is_unassigned desc, sequence, id"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer()
    area_id = fields.Many2one(
        comodel_name="work.center.area",
        string="Work Area",
        required=True,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        index=True,
        ondelete="restrict",
        tracking=True,
        help="Set: the station is at operating unit level — it only takes "
        "documents of this operating unit, and only those can be diverted to "
        "it. Empty: the station is central and takes any operating unit.",
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        relation="work_center_member_rel",
        column1="work_center_id",
        column2="user_id",
        string="Station Members",
        help="People who may act on the documents at this station, within "
        "their own role: membership narrows, it never grants. With no members "
        "the station is open to everyone holding the role. Members also "
        "forward, divert and send back the documents here.",
    )
    allowed_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_allowed_act_rel",
        column1="work_center_id",
        column2="act_id",
        string="Allowed Acts",
        domain=[("kind", "=", "act")],
        context={"active_test": False},
        help="The acts offered at this station.",
    )
    required_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_required_act_rel",
        column1="work_center_id",
        column2="act_id",
        string="Required Acts",
        domain=[("kind", "=", "act")],
        context={"active_test": False},
        help="Acts that must be done during a visit before the document is "
        "forwarded. Forwarding without one needs a reason, which is logged.",
    )
    allowed_edit_ids = fields.Many2many(
        comodel_name="work.center.act",
        relation="work_center_allowed_edit_rel",
        column1="work_center_id",
        column2="act_id",
        string="Editable Parts",
        domain=[("kind", "=", "edit")],
        context={"active_test": False},
        help="The parts of the document that may be edited while it is here. "
        "They are permissions, not acts, and are never required.",
    )
    area_model_ids = fields.Many2many(related="area_id.model_ids")
    is_my_station = fields.Boolean(
        string="My Station",
        compute="_compute_is_my_station",
        search="_search_is_my_station",
        help="Technical: I am a member, or the station has no members and I "
        "hold the role of one of its acts.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Leave empty to share the station with every company.",
    )
    is_unassigned = fields.Boolean(
        string="Unassigned Card",
        readonly=True,
        copy=False,
        help="The synthetic Unassigned card of a work area: it counts the "
        "documents in the circuit that no rule placed at a station. Documents "
        "never point to it; a station administrator moves them on.",
    )
    rule_ids = fields.One2many(
        comodel_name="work.center.rule",
        inverse_name="work_center_id",
        string="Routing Rules",
        groups="work_center.group_work_center_manager",
    )
    assignment_rule_ids = fields.One2many(
        comodel_name="work.center.assignment.rule",
        inverse_name="work_center_id",
        string="Assignment Rules",
        groups="work_center.group_work_center_manager",
    )
    document_model = fields.Char(
        compute="_compute_document_model",
        search="_search_document_model",
        help="Search helper: stations whose area covers this model "
        "(ir.model is not readable by regular users).",
    )
    counter_data = fields.Json(string="Counters", compute="_compute_counter_data")

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The station code must be unique per company.",
        ),
    ]

    @api.constrains("is_unassigned", "operating_unit_id")
    def _check_unassigned_central(self):
        if self.filtered(lambda wc: wc.is_unassigned and wc.operating_unit_id):
            raise ValidationError(
                _("The Unassigned card cannot belong to an operating unit.")
            )

    @api.constrains("allowed_act_ids", "required_act_ids")
    def _check_required_within_allowed(self):
        for station in self:
            if station.required_act_ids.filtered(lambda act: act.kind != "act"):
                raise ValidationError(_("An editable part cannot be required."))
            missing = station.required_act_ids - station.allowed_act_ids
            if missing:
                raise ValidationError(
                    _("%(act)s is required at %(station)s but not allowed there.")
                    % {"act": missing[0].name, "station": station.name}
                )

    @api.constrains("area_id", "allowed_act_ids", "required_act_ids", "allowed_edit_ids")
    def _check_acts_within_area(self):
        for station in self:
            models = station.area_id.sudo().model_ids
            acts = (
                station.allowed_act_ids
                | station.required_act_ids
                | station.allowed_edit_ids
            )
            stray = acts.filtered(lambda act: act.model_id not in models)
            if stray:
                raise ValidationError(
                    _("%(act)s does not belong to a document model of %(area)s.")
                    % {"act": stray[0].name, "area": station.area_id.name}
                )

    @api.constrains("area_id", "is_unassigned", "allowed_act_ids", "member_ids")
    def _check_station_has_substance(self):
        """The Unassigned card carries nothing; a real station needs an act to
        offer or someone to hand the work to. Seeded stations (loaded with
        ``install_mode``) start empty until an administrator configures them."""
        for station in self:
            if station.is_unassigned:
                if (
                    station.allowed_act_ids
                    or station.required_act_ids
                    or station.allowed_edit_ids
                    or station.member_ids
                ):
                    raise ValidationError(
                        _("The Unassigned card has no acts, editable parts or members.")
                    )
            elif not (
                self.env.context.get("install_mode")
                or station.allowed_act_ids
                or station.member_ids
            ):
                raise ValidationError(
                    _("Station %s needs at least one allowed act or one member.")
                    % station.name
                )

    def _compute_document_model(self):
        self.document_model = False

    def _compute_is_my_station(self):
        mine = self.search([("id", "in", self.ids), ("is_my_station", "=", True)])
        for station in self:
            station.is_my_station = station in mine

    def _search_is_my_station(self, operator, value):
        """Member, or memberless and holding one of the station's act roles.
        Same shape as mail_activity_todo's ``_search_is_my_todo``."""
        user = self.env.user
        mine = [
            "|",
            ("member_ids", "in", [user.id]),
            "&",
            ("member_ids", "=", False),
            ("allowed_act_ids.group_id", "in", user.groups_id.ids),
        ]
        positive = (operator == "=") == bool(value)
        ids = self.with_context(active_test=False).search(mine).ids
        return [("id", "in" if positive else "not in", ids)]

    def _search_document_model(self, operator, value):
        areas = (
            self.env["work.center.area"]
            .sudo()
            .search([("model_ids.model", operator, value)])
        )
        return [("area_id", "in", areas.ids)]

    def unlink(self):
        if not self.env.context.get("work_center_area_unlink") and self.filtered(
            "is_unassigned"
        ):
            raise UserError(_("The Unassigned card cannot be deleted."))
        if self.env["work.center.visit"].sudo().search_count(
            [("work_center_id", "in", self.ids)]
        ):
            raise UserError(
                _(
                    "A station that documents have visited cannot be deleted: "
                    "archive it instead."
                )
            )
        return super().unlink()

    # ------------------------------------------------------------------
    # Authority and responsibility (read through sudo: the operating unit
    # record rule can hide the station from the very person acting)
    # ------------------------------------------------------------------
    def _active_members(self):
        self.ensure_one()
        return self.sudo().member_ids.filtered(lambda u: u.active and not u.share)

    def _responsible_users(self):
        """Who is responsible for a document at this station, and why:
        its members; else the active holders of the roles of its allowed acts;
        else — only when nobody is left — the station administrators."""
        self.ensure_one()
        station = self.sudo()
        members = station._active_members()
        if members:
            return members, "members"
        groups = station.allowed_act_ids.filtered(
            lambda act: act.active and act.group_id
        ).group_id
        holders = groups.users.filtered(lambda u: u.active and not u.share)
        if holders:
            return holders, "role"
        admins = self.env.ref("work_center.group_work_center_manager").sudo().users
        return admins.filtered(lambda u: u.active and not u.share), "fallback"

    def action_apply_assignment_rules(self):
        """Assign, by the rules, the documents at the station that nobody
        holds yet (those that arrived before the rules were set)."""
        for station in self:
            for model_name in station.assignment_rule_ids.mapped("model_name"):
                self.env[model_name].sudo().search(
                    [
                        ("work_center_id", "=", station.id),
                        ("work_center_assignee_id", "=", False),
                    ]
                )._work_center_auto_assign()
        return True

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    def _counter_base_domain(self, model_name):
        """The documents a card counts. The Unassigned card counts the ones in
        the circuit that no station holds, not every document without one."""
        self.ensure_one()
        if self.is_unassigned:
            return expression.AND(
                [
                    [("work_center_id", "=", False)],
                    self.env[model_name]._work_center_circuit_domain(),
                ]
            )
        return [("work_center_id", "=", self.id)]

    @api.depends_context("uid")
    def _compute_counter_data(self):
        """Card counters, counted with the viewer's own rights so each number
        equals the list it opens. One read_group per counter."""
        data = {wc: [] for wc in self}
        saved = self.filtered("id")
        counters = self.env["work.center.counter"].search(
            [("area_id", "in", saved.area_id.ids)]
        )
        for counter in counters:
            Model = self.env[counter.model_name]
            if not Model.check_access_rights("read", raise_exception=False):
                continue
            domain = counter._get_domain()
            wcs = saved.filtered(lambda wc, c=counter: wc.area_id == c.area_id)
            assigned = wcs.filtered(lambda wc: not wc.is_unassigned)
            counts = {}
            if assigned:
                groups = Model.read_group(
                    expression.AND([domain, [("work_center_id", "in", assigned.ids)]]),
                    ["work_center_id"],
                    ["work_center_id"],
                    lazy=False,
                )
                counts = {g["work_center_id"][0]: g["__count"] for g in groups}
            unassigned = wcs - assigned
            if unassigned:
                count = Model.search_count(
                    expression.AND(
                        [domain, unassigned[:1]._counter_base_domain(counter.model_name)]
                    )
                )
                counts.update({wc.id: count for wc in unassigned})
            for wc in wcs:
                data[wc].append(
                    {
                        "id": counter.id,
                        "name": counter.name,
                        "count": counts.get(wc.id, 0),
                        "color": counter.color,
                    }
                )
        for wc in self:
            # A Json field stores an empty list as False; the kanban template
            # guards for it (``raw_value or []``).
            wc.counter_data = data[wc]

    def action_open_counter(self):
        """Open the documents behind one card counter (the counter id comes
        from the kanban button's context)."""
        self.ensure_one()
        counter = (
            self.env["work.center.counter"]
            .browse(self.env.context.get("work_center_counter_id"))
            .exists()
        )
        if not counter:
            raise UserError(_("This counter no longer exists."))
        return {
            "type": "ir.actions.act_window",
            "name": "%s · %s" % (self.name, counter.name),
            "res_model": counter.model_name,
            "view_mode": "tree,form",
            "views": [(False, "list"), (False, "form")],
            "domain": expression.AND(
                [self._counter_base_domain(counter.model_name), counter._get_domain()]
            ),
            "context": {"create": False},
        }
