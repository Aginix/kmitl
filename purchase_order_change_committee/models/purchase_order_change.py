from odoo import api, fields, models


class PurchaseOrderChange(models.Model):
    _inherit = "purchase.order.change"

    committee_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.snapshot",
        inverse_name="change_id",
        string="Committee Snapshots",
    )
    old_wa_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.snapshot",
        inverse_name="change_id",
        string="WA Committee (Before)",
        domain=[
            ("committee_type", "=", "work_acceptance"),
            ("snapshot_type", "=", "before"),
        ],
    )
    new_wa_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.snapshot",
        inverse_name="change_id",
        string="WA Committee (After)",
        domain=[
            ("committee_type", "=", "work_acceptance"),
            ("snapshot_type", "=", "after"),
        ],
    )
    old_ws_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.snapshot",
        inverse_name="change_id",
        string="Work Supervisor (Before)",
        domain=[
            ("committee_type", "=", "work_supervisor"),
            ("snapshot_type", "=", "before"),
        ],
    )
    new_ws_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.snapshot",
        inverse_name="change_id",
        string="Work Supervisor (After)",
        domain=[
            ("committee_type", "=", "work_supervisor"),
            ("snapshot_type", "=", "after"),
        ],
    )
    has_wa_snapshot = fields.Boolean(
        compute="_compute_has_snapshots",
        store=False,
    )
    has_ws_snapshot = fields.Boolean(
        compute="_compute_has_snapshots",
        store=False,
    )

    @api.depends("committee_snapshot_ids")
    def _compute_has_snapshots(self):
        for rec in self:
            snapshots = rec.committee_snapshot_ids
            rec.has_wa_snapshot = any(
                s.committee_type == "work_acceptance" for s in snapshots
            )
            rec.has_ws_snapshot = any(
                s.committee_type == "work_supervisor" for s in snapshots
            )

    @api.depends("change_field_ids", "committee_snapshot_ids")
    def _compute_has_change_fields(self):
        super()._compute_has_change_fields()
        for rec in self:
            if rec.committee_snapshot_ids:
                rec.has_change_fields = True

    @api.model
    def _get_change_type_section_map(self):
        res = super()._get_change_type_section_map()
        res.setdefault("none", []).extend(
            [
                "purchase_order_change_committee.purchase_change_section_wa_committee",
                "purchase_order_change_committee.purchase_change_section_work_supervisor",
            ]
        )
        return res
