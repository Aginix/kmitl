from odoo import api, fields, models


class PurchaseOrderChange(models.Model):
    _inherit = "purchase.order.change"

    installment_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.installment.snapshot",
        inverse_name="change_id",
        string="Installment Snapshots",
    )
    old_installment_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.installment.snapshot",
        inverse_name="change_id",
        string="งวดงาน (เดิม)",
        domain=[("snapshot_type", "=", "before")],
    )
    new_installment_snapshot_ids = fields.One2many(
        comodel_name="purchase.order.change.installment.snapshot",
        inverse_name="change_id",
        string="งวดงาน (ใหม่)",
        domain=[("snapshot_type", "=", "after")],
    )
    has_installment_snapshot = fields.Boolean(
        compute="_compute_has_installment_snapshot",
        store=False,
    )

    @api.depends("installment_snapshot_ids")
    def _compute_has_installment_snapshot(self):
        for rec in self:
            rec.has_installment_snapshot = bool(rec.installment_snapshot_ids)

    @api.depends("change_field_ids", "installment_snapshot_ids")
    def _compute_has_change_fields(self):
        super()._compute_has_change_fields()
        for rec in self:
            if rec.installment_snapshot_ids:
                rec.has_change_fields = True

    @api.model
    def _get_change_type_section_map(self):
        res = super()._get_change_type_section_map()
        res.setdefault("impact", []).append(
            "purchase_order_change_installment.purchase_change_section_installment"
        )
        return res
