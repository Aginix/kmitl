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
        string="ศูนย์งาน",
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
        string="ศูนย์งานกำหนดเอง",
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

    def _work_center_match(self):
        self.ensure_one()
        return self.env["work.center.rule"].sudo()._match(self)

    @api.depends(lambda self: self._work_center_routing_fields())
    def _compute_work_center_id(self):
        for rec in self:
            if rec._work_center_is_routable() and not rec.work_center_manual:
                rec.work_center_id = rec._work_center_match()
            # Otherwise assign nothing: the stored value is kept (sticky).

    @api.constrains("work_center_id")
    def _check_work_center_id(self):
        if self.filtered("work_center_id.is_unassigned"):
            raise ValidationError(
                _("A document cannot be put on the 'ยังไม่มีศูนย์งาน' card.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        manual = records.browse(
            rec.id
            for rec, vals in zip(records, vals_list)
            if "work_center_id" in vals and "work_center_manual" not in vals
        )
        manual._work_center_update_pin()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "work_center_id" in vals and "work_center_manual" not in vals:
            self._work_center_update_pin()
        return res

    def _work_center_update_pin(self):
        """After a hand-written work center: pin it when it differs from the
        rules; on clear, un-pin and (while routable) follow the rules again."""
        for rec in self:
            if rec.work_center_id:
                pinned = rec.work_center_id != rec._work_center_match()
                if rec.work_center_manual != pinned:
                    rec.write({"work_center_manual": pinned})
            else:
                routed = (
                    rec._work_center_match()
                    if rec._work_center_is_routable()
                    else rec.work_center_id
                )
                if rec.work_center_manual or routed:
                    rec.write(
                        {"work_center_manual": False, "work_center_id": routed.id}
                    )
