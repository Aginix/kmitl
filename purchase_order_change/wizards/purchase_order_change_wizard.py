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
    work_start = fields.Date(string="Work Start")
    date_order_date = fields.Date(string="Order Date")
    contract_period_days = fields.Integer(string="Contract Period Days")
    contract_name = fields.Char(string="Contract Name")
    contract_number = fields.Char(string="Contract No.")
    show_fines_fields = fields.Boolean()
    show_work_fields = fields.Boolean()
    show_contract_fields = fields.Boolean()

    @api.onchange("change_id")
    def _compute_visible_fields(self):
        for rec in self:
            print('===============================>', rec.section_ids)
            xml_ids_map = rec.section_ids.get_external_id()
            xml_id_list = [xml.split(".")[-1] for xml in xml_ids_map.values()]

            rec.show_fines_fields = "purchase_change_section_1" in xml_id_list
            rec.show_work_fields = "purchase_change_section_2" in xml_id_list
            rec.show_contract_fields = "purchase_change_section_3" in xml_id_list

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)

        default_section_ids = self.env.context.get("default_section_ids")
        if default_section_ids and isinstance(default_section_ids, list):
            ids = default_section_ids[0][2]
        else:
            ids = []

        sections = self.env["purchase.change.section"].browse(ids)

        xml_ids_map = sections.get_external_id()
        xml_id_list = [xml.split(".")[-1] for xml in xml_ids_map.values()]

        vals["show_fines_fields"] = "purchase_change_section_1" in xml_id_list
        vals["show_work_fields"] = "purchase_change_section_2" in xml_id_list
        vals["show_contract_fields"] = "purchase_change_section_3" in xml_id_list

        return vals

    @api.constrains("work_start", "date_order_date")
    def _check_work_start(self):
        for rec in self:
            if not rec.show_work_fields:
                continue

            if rec.work_start and rec.date_order_date:
                if rec.work_start < rec.date_order_date:
                    raise ValidationError(
                        _("Work Start Date must be greater than or equal to Order Date.")
                    )

    def action_save_changes(self):
        self.ensure_one()
        po = self.purchase_id.sudo()
        track_fields = {
            "fines_rate": "อัตราค่าปรับ",
            "fines_late": "ค่าปรับล่าช้า",
            "late_days": "จำนวนวันล่าช้า",
            "supervision_cost": "ค่าควบคุมงาน",
            "work_start": "วันที่เริ่มงาน",
            "date_order_date": "วันที่ลงนามสัญญา",
            "contract_period_days": "กำหนดวันส่งมอบภายใน",
            "contract_name": "ชื่อสัญญา",
            "contract_number": "เลขที่สัญญา",
        }

        ChangeField = self.env["purchase.order.change.field"].sudo()

        for field_name, label in track_fields.items():
            old_value = po[field_name]
            new_value = self[field_name]

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

        return {"type": "ir.actions.act_window_close"}
