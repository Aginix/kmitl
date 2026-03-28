# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChange(models.Model):
    _name = 'purchase.order.change'
    _description = 'Purchase Order Change'

    number = fields.Integer(string='Number')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    change_type = fields.Selection(selection=[('none', 'None'), ('impact', 'Impact')])
    section_ids = fields.Many2many(comodel_name="purchase.change.section")
    purchase_id = fields.Many2one(comodel_name="purchase.order")
    change_field_ids = fields.One2many(
        comodel_name='purchase.order.change.field',
        inverse_name='change_id',
        string='Change Fields'
    )
    editor_id = fields.Many2one(comodel_name="res.users", string="Editor", default=lambda self: self.env.user)
    has_change_fields = fields.Boolean(
        compute="_compute_has_change_fields",
        store=False
    )
    allowed_section_ids = fields.Many2many(
        comodel_name="purchase.change.section",
        compute="_compute_allowed_sections",
        store=False,
    )
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
    )
    has_sections = fields.Boolean(
    compute="_compute_has_sections",
    store=False
    )

    @api.depends("section_ids")
    def _compute_has_sections(self):
        for rec in self:
            rec.has_sections = bool(rec.section_ids)

    @api.model
    def _get_change_type_section_map(self):
        """
        ในอนาคต จะใช้การ ihnerit แบบนี้ เพื่อเพิ่ม section type ใหม่ ๆ ได้ง่ายขึ้น

        @api.model
        def _get_change_type_section_map(self):
            res = super()._get_change_type_section_map()

            res.setdefault("impact", []).append(
                "purchase_order_change.purchase_change_section_4"
            )
            res.setdefault("none", []).append(
                "purchase_order_change.purchase_change_section_4"
            )

            return res
        """
        return {
            "impact": [
                "purchase_order_change.purchase_change_section_2",
            ],
            "none": [
                "purchase_order_change.purchase_change_section_1",
                "purchase_order_change.purchase_change_section_3",
            ],
        }

    @api.depends("change_type")
    def _compute_allowed_sections(self):
        section_map = self._get_change_type_section_map()

        for rec in self:
            xml_ids = section_map.get(rec.change_type, [])
            rec.allowed_section_ids = [
                self.env.ref(xml_id).id
                for xml_id in xml_ids
                if xml_id
            ] or [(5, 0, 0)]

    @api.onchange("change_type")
    def _onchange_change_type(self):
        self.section_ids = [(5, 0, 0)]

    @api.depends("change_field_ids")
    def _compute_has_change_fields(self):
        for rec in self:
            rec.has_change_fields = bool(rec.change_field_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("number", "New") in (False, "New"):
                purchase_id = (vals.get("purchase_id") or self.env.context.get("default_purchase_id"))
                sequence = self._get_or_create_po_sequence(purchase_id)
                vals["number"] = sequence.next_by_code(f"purchase.order.change.po_{purchase_id}")
        return super().create(vals_list)

    def _get_or_create_po_sequence(self, purchase_id):

        seq_code = f"purchase.order.change.po_{purchase_id}"
        sequence = self.env["ir.sequence"].sudo().search(
            [("code", "=", seq_code)],
            limit=1,
        )

        if not sequence:
            sequence = self.env["ir.sequence"].sudo().create({
                "name": _("PO Change %s") % purchase_id,
                "code": seq_code,
                "padding": 1,
                "number_next": 1,
            })

        return sequence

    def action_done(self):
        for record in self:
            po = record.purchase_id.sudo()

            vals = {}

            for line in record.change_field_ids:
                field = line.field_id
                field_name = field.name
                new_value = line.new_value

                if field.ttype in ("many2many", "one2many"):
                    continue
                # แปลงค่าตาม type
                if field.ttype in ("float", "monetary"):
                    try:
                        converted = float(new_value)
                    except:
                        converted = 0.0

                elif field.ttype == "integer":
                    try:
                        converted = int(new_value)
                    except:
                        converted = 0

                elif field.ttype == "boolean":
                    converted = new_value.lower() in ("1", "true", "yes")

                elif field.ttype == "date":
                    converted = new_value

                elif field.ttype == "many2one":
                    try:
                        converted = int(new_value)
                    except:
                        converted = False

                else:
                    converted = new_value

                vals[field_name] = converted

            if vals:
                po.write(vals)

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _prepare_wizard_context(self, extra_context=None):
        self.ensure_one()

        base_context = {
            "default_change_id": self.id,
            "default_purchase_id": self.purchase_id.id,
            "default_work_start": self.purchase_id.work_start,
            "default_contract_period_days": self.purchase_id.contract_period_days,
            "default_date_order_date": self.purchase_id.date_order_date,
            "default_fines_rate": self.purchase_id.fines_rate,
            "default_fines_late": self.purchase_id.fines_late,
            "default_late_days": self.purchase_id.late_days,
            "default_supervision_cost": self.purchase_id.supervision_cost,
            "default_section_ids": [(6, 0, self.section_ids.ids)],
            "default_contract_name": self.purchase_id.contract_name,
            "default_contract_number": self.purchase_id.contract_number,
        }

        if extra_context:
            base_context.update(extra_context)

        return base_context

    def action_next(self):
        return {
            "name": "Change Purchase Order",
            "type": "ir.actions.act_window",
            "res_model": "purchase.order.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": self._prepare_wizard_context(),
        }
