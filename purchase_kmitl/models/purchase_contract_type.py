# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseContractType(models.Model):
    _name = "purchase.contract.type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "PurchaseContractType"

    name = fields.Char(tracking=True, required=True)
    active = fields.Boolean(tracking=True, default=True)
    is_construction = fields.Boolean(
        string="สัญญาจ้างก่อสร้าง",
        tracking=True,
        help="หากติ๊ก จะแสดงแท็บ 'วันที่ดำเนินงาน' ใน Work Acceptance",
    )
    purchase_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="contract_type_id",
    )

    def unlink(self):
        for rec in self:
            if rec.purchase_ids:
                raise UserError(
                    _("You cannot delete a contract type (%s) that is used in purchase order")
                    % rec.name
                )
        return super().unlink()
