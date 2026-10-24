from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class WorkCenter(models.Model):
    """ศูนย์งาน — the unit that owns and tracks a document (see ADR-0001).

    Documents carry a stored ``work_center_id`` stamped by routing rules while
    they are draft. Membership only says whose overview the card belongs to:
    it grants and restricts nothing. With an operating unit the work center is
    หน่วยงาน-level (its rules only match documents of that OU); without one it
    is ส่วนกลาง-level.
    """

    _name = "work.center"
    _description = "Work Center"
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
        help="Set: the work center is at operating unit level — routing rules "
        "only match documents of this operating unit. Empty: the work center "
        "is central — its rules match any operating unit.",
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        relation="work_center_member_rel",
        column1="work_center_id",
        column2="user_id",
        string="Members",
        help="People who follow this work center's documents. Membership only "
        "puts the card on their overview; it grants no access.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Leave empty to share the work center with every company.",
    )
    is_unassigned = fields.Boolean(
        string="Unassigned Card",
        readonly=True,
        copy=False,
        help="The synthetic Unassigned card of a work area: it counts "
        "documents that have no work center. Documents never point to it.",
    )
    rule_ids = fields.One2many(
        comodel_name="work.center.rule",
        inverse_name="work_center_id",
        string="Routing Rules",
        groups="work_center.group_work_center_manager",
    )
    document_model = fields.Char(
        compute="_compute_document_model",
        search="_search_document_model",
        help="Search helper: work centers whose area covers this model "
        "(ir.model is not readable by regular users).",
    )
    counter_data = fields.Json(string="Counters", compute="_compute_counter_data")

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The work center code must be unique per company.",
        ),
    ]

    @api.constrains("is_unassigned", "operating_unit_id")
    def _check_unassigned_central(self):
        if self.filtered(lambda wc: wc.is_unassigned and wc.operating_unit_id):
            raise ValidationError(
                _("The Unassigned card cannot belong to an operating unit.")
            )

    def _compute_document_model(self):
        self.document_model = False

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
        return super().unlink()

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    def _counter_base_domain(self):
        self.ensure_one()
        return [("work_center_id", "=", False if self.is_unassigned else self.id)]

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
                    expression.AND([domain, [("work_center_id", "=", False)]])
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
                [self._counter_base_domain(), counter._get_domain()]
            ),
            "context": {"create": False},
        }
