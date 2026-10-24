from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WorkCenterMixin(models.AbstractModel):
    """Stamps a document with the ศูนย์งาน that owns and tracks it (ADR-0001).

    * While the document is routable (draft by default) ``work_center_id``
      follows the routing rules whenever a routing field changes.
    * Out of draft it is sticky: the compute assigns nothing, so the stored
      value stays. It remains editable by hand in every state.
    * A work center picked by hand that differs from what the rules would give
      pins the document (``work_center_manual``) — rules stop touching it.
      Clearing the field un-pins it and, while draft, routes it again.

    Consumers inherit the mixin next to ``mail.thread`` (for tracking) and may
    extend ``_work_center_routing_fields`` / ``_work_center_is_routable``.
    """

    _name = "work.center.mixin"
    _description = "Work Center Mixin"
    _work_center_ou_field = "operating_unit_id"

    work_center_id = fields.Many2one(
        comodel_name="work.center",
        string="Work Center",
        index=True,
        copy=False,
        tracking=True,
        ondelete="restrict",
        compute="_compute_work_center_id",
        store=True,
        readonly=False,
        domain=lambda self: [
            ("is_unassigned", "=", False),
            ("document_model", "=", self._name),
        ],
    )
    work_center_manual = fields.Boolean(
        string="Work Center Pinned",
        copy=False,
        help="Set when the work center was picked by hand: routing rules no "
        "longer change it. Clear the work center to follow the rules again.",
    )

    @api.model
    def _valid_field_parameter(self, field, name):
        # ``tracking`` is only meaningful once a consumer adds mail.thread.
        return name == "tracking" or super()._valid_field_parameter(field, name)

    @api.model
    def _work_center_routing_fields(self):
        """Fields whose change re-routes a routable document."""
        field = self._work_center_ou_field
        return [field] if field in self._fields else []

    def _work_center_is_routable(self):
        self.ensure_one()
        return self.state == "draft"

    def _work_center_rules(self):
        """The routing rules of this model, searched once per batch."""
        return self.env["work.center.rule"].sudo()._candidate_rules(self._name)

    def _work_center_match(self, rules):
        self.ensure_one()
        return self.env["work.center.rule"].sudo()._match(self, rules)

    @api.depends(lambda self: self._work_center_routing_fields())
    def _compute_work_center_id(self):
        rules = None
        for rec in self:
            if rec._work_center_is_routable() and not rec.work_center_manual:
                if rules is None:
                    rules = self._work_center_rules()
                rec.work_center_id = rec._work_center_match(rules)
            # Otherwise assign nothing: the stored value is kept (sticky).

    @api.constrains("work_center_id")
    def _check_work_center_id(self):
        if self.filtered("work_center_id.is_unassigned"):
            raise ValidationError(_("A document cannot be put on the Unassigned card."))

    def _work_center_stamp(self):
        """Resolve the pending routing now.

        The compute is lazy, so a document created in draft and submitted in
        the same transaction would run it only once it is out of draft — and
        then it assigns nothing and the document is never stamped. Flushing the
        field pins the routing to the state the document was actually in.
        """
        self.flush_recordset(["work_center_id"])

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        manual = records.browse(
            rec.id
            for rec, vals in zip(records, vals_list)
            if "work_center_id" in vals and "work_center_manual" not in vals
        )
        manual._work_center_update_pin()
        (records - manual)._work_center_stamp()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "work_center_id" in vals and "work_center_manual" not in vals:
            self._work_center_update_pin()
        elif any(name in vals for name in self._work_center_routing_fields()):
            self._work_center_stamp()
        return res

    def _work_center_update_pin(self):
        """After a hand-written work center: pin it when it differs from the
        rules; on clear, un-pin and (while routable) follow the rules again."""
        if not self:
            return
        rules = self._work_center_rules()
        to_pin = self.browse()
        to_unpin = self.browse()
        to_route = {}
        for rec in self:
            if rec.work_center_id:
                pinned = rec.work_center_id != rec._work_center_match(rules)
                if rec.work_center_manual == pinned:
                    continue
                if pinned:
                    to_pin |= rec
                else:
                    to_unpin |= rec
            else:
                routed = (
                    rec._work_center_match(rules)
                    if rec._work_center_is_routable()
                    else rec.work_center_id
                )
                if rec.work_center_manual or routed:
                    to_route.setdefault(routed.id, self.browse())
                    to_route[routed.id] |= rec
        if to_pin:
            to_pin.write({"work_center_manual": True})
        if to_unpin:
            to_unpin.write({"work_center_manual": False})
        for work_center_id, records in to_route.items():
            records.write(
                {"work_center_manual": False, "work_center_id": work_center_id}
            )
