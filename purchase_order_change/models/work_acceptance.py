# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    is_work_end_extended = fields.Boolean(
        compute="_compute_is_work_end_extended",
        store=True,
    )

    @api.depends(
        "purchase_id.work_end",
        "purchase_id.change_ids.change_field_ids.field_id",
        "po_work_end_original",
    )
    def _compute_is_work_end_extended(self):
        accepted = self.filtered(lambda r: r.state == 'accept')
        if accepted:
            self.env.cr.execute(
                "SELECT id, is_work_end_extended FROM work_acceptance"
                " WHERE id = ANY(%s)",
                [list(accepted.ids)],
            )
            stored = dict(self.env.cr.fetchall())
            for rec in accepted:
                rec.is_work_end_extended = stored.get(rec.id, False)
        work_end_fields = {"work_start", "contract_period_days"}
        for rec in (self - accepted):
            has_work_end_change = any(
                cf.field_id.name in work_end_fields
                for change in rec.purchase_id.change_ids
                for cf in change.change_field_ids
            )
            rec.is_work_end_extended = (
                has_work_end_change
                or rec.purchase_id.work_end > rec.po_work_end_original
            )
