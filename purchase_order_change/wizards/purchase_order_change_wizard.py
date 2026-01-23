# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChangeWizard(models.TransientModel):
    _name = 'purchase.order.change.wizard'
    _description = _('PurchaseOrderChangeWizard')

    change_id = fields.Many2one("purchase.order.change", string="Change Record")
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    fines_late = fields.Monetary(string="Fines Amount")
    late_days = fields.Integer(string="Late Days")
    currency_id = fields.Many2one(
        "res.currency",
        related="purchase_id.currency_id",
        readonly=True
    )
    section_ids = fields.Many2many("purchase.change.section")
    fines_rate = fields.Monetary(string="Fines Rate")
    supervision_cost = fields.Monetary(string="Supervision Cost")
    work_start = fields.Date(string="Work Start")
    date_order_date = fields.Date(string="Order Date")
    contract_period_days = fields.Integer(string="Contract Period Days")
    contract_name = fields.Char(string="Contract Name")
    contract_number = fields.Char(string="Contract No.")
    fines_rate_old = fields.Monetary(string="Old Fines Rate", readonly=True)
    supervision_cost_old = fields.Monetary(string="Old Supervision Cost", readonly=True)
    work_start_old = fields.Date(string="Old Work Start", readonly=True)
    date_order_date_old = fields.Date(string="Old Order Date", readonly=True)
    contract_period_days_old = fields.Integer(string="Old Contract Period", readonly=True)
    contract_name_old = fields.Char(string="Old Contract Name", readonly=True)
    contract_number_old = fields.Char(string="Old Contract No.", readonly=True)
    show_fines_fields = fields.Boolean()
    show_work_fields = fields.Boolean()
    show_contract_fields = fields.Boolean()

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)

        purchase = self._get_default_purchase()
        if purchase:
            vals.update(self._prepare_old_values(purchase))

        section_xml_ids = self._get_default_section_xml_ids()
        vals.update(self._prepare_section_visibility(section_xml_ids))

        return vals

    def _get_default_purchase(self):
        purchase_id = self.env.context.get("default_purchase_id")
        if not purchase_id:
            return False
        return self.env["purchase.order"].browse(purchase_id)

    def _prepare_old_values(self, purchase):
        """ ตัวอย่างการขยาย method
            def _prepare_old_values(self, purchase):
                vals = super()._prepare_old_values(purchase)
                vals["new_field_old"] = purchase.new_field
                return vals
        """
        return {
            "fines_rate_old": purchase.fines_rate,
            "supervision_cost_old": purchase.supervision_cost,

            "work_start_old": purchase.work_start,
            "date_order_date_old": purchase.date_order_date,
            "contract_period_days_old": purchase.contract_period_days,

            "contract_name_old": purchase.contract_name,
            "contract_number_old": purchase.contract_number,
        }

    def _get_default_section_xml_ids(self):
        default_section_ids = self.env.context.get("default_section_ids")

        if default_section_ids and isinstance(default_section_ids, list):
            ids = default_section_ids[0][2]
        else:
            ids = []

        sections = self.env["purchase.change.section"].browse(ids)

        xml_ids_map = sections.get_external_id()
        return [xml.split(".")[-1] for xml in xml_ids_map.values()]

    def _prepare_section_visibility(self, section_xml_ids):
        """ ตัวอย่างการขยาย method
        def _prepare_section_visibility(self, section_xml_ids):
            vals = super()._prepare_section_visibility(section_xml_ids)
            vals["show_new_section"] = "purchase_change_section_4" in section_xml_ids
            return vals
        """
        return {
            "show_fines_fields": "purchase_change_section_1" in section_xml_ids,
            "show_work_fields": "purchase_change_section_2" in section_xml_ids,
            "show_contract_fields": "purchase_change_section_3" in section_xml_ids,
        }

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

    def _save_changes(self, track_fields):
        self.ensure_one()

        po = self.purchase_id.sudo()
        ChangeField = self.env["purchase.order.change.field"].sudo()

        model_fields = self.env["ir.model.fields"].search_read(
            [("model", "=", "purchase.order"), ("name", "in", list(track_fields.keys()))],
            ["id", "name"]
        )
        field_map = {m["name"]: m["id"] for m in model_fields}

        for field_name, label in track_fields.items():
            old_value = po[field_name]
            new_value = self[field_name]

            if old_value != new_value:
                ChangeField.create({
                    "change_id": self.change_id.id,
                    "field_name": label,
                    "field_id": field_map.get(field_name),
                    "old_value": self._format_value(old_value),
                    "new_value": self._format_value(new_value),
                })

        return self.change_id.action_done()

    def _format_value(self, value):
        if not value:
            return ""

        if hasattr(value, "_name"):
            if len(value) > 1:
                return ", ".join(
                    value.mapped(lambda r: r.display_name or r.name)
                )

            return value.display_name or value.name or ""

        return str(value)

    def _get_track_fields(self):
        return {
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

    def action_save_changes(self):
        track_fields = self._get_track_fields()
        return self._save_changes(track_fields)

    def cancel(self):
        for wizard in self:
            if wizard.change_id:
                wizard.change_id.sudo().unlink()

            if wizard.purchase_id:
                seq_code = f"purchase.order.change.po_{wizard.purchase_id.id}"
                seq = self.env["ir.sequence"].sudo().search(
                    [("code", "=", seq_code)],
                    limit=1,
                )
                if seq:
                    seq.number_next_actual -= 1
