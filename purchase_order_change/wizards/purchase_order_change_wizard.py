# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChangeWizard(models.TransientModel):
    _name = 'purchase.order.change.wizard'
    _description = _('PurchaseOrderChangeWizard')

    change_id = fields.Many2one("purchase.order.change", string="Change Record")
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    fines_rate = fields.Monetary(string="Fines Rate")
    fines_late = fields.Monetary(string="Fines Amount")
    late_days = fields.Integer(string="Late Days")
    supervision_cost = fields.Monetary(string="Supervision Cost")
    currency_id = fields.Many2one(
        "res.currency",
        related="purchase_id.currency_id",
        readonly=True
    )
    section_ids = fields.Many2many("purchase.change.section")

    def action_save_changes(self):
        self.ensure_one()
        po = self.purchase_id.sudo()
        track_fields = {
            "fines_rate": "อัตราค่าปรับ",
            "fines_late": "ค่าปรับล่าช้า",
            "late_days": "จำนวนวันล่าช้า",
            "supervision_cost": "ค่าควบคุมงาน",
        }

        ChangeField = self.env["purchase.order.change.field"].sudo()

        for field_name, label in track_fields.items():
            old_value = po[field_name]
            new_value = self[field_name]

            # ถ้าเปลี่ยนจริง
            if old_value != new_value:

                ChangeField.create({
                    "change_id": self.change_id.id,
                    "field_name": label,
                    "old_value": str(old_value or ''),
                    "new_value": str(new_value or ''),
                    "field_id": self.env["ir.model.fields"].search([
                        ("model", "=", "purchase.order"),
                        ("name", "=", field_name)
                    ], limit=1).id,
                })

        po.write({
            "fines_rate": self.fines_rate,
            "fines_late": self.fines_late,
            "late_days": self.late_days,
            "supervision_cost": self.supervision_cost,
        })

        return {"type": "ir.actions.act_window_close"}

    is_addition_section = fields.Boolean(
        string="Is Addition Section",
        compute="_compute_is_addition_section",
        store=False
    )

    @api.depends("section_ids")
    def _compute_is_addition_section(self):
        for rec in self:
            rec.is_addition_section = any(
                sec.section_type == "addition" for sec in rec.section_ids
            )
