# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SarabunReference(models.Model):
    _name = "sarabun.reference"
    _description = "Sarabun Document Reference"
    _order = "id"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Generic reference using res_model/res_id pattern
    res_model = fields.Selection(
        selection=[
            ("purchase.request", "Purchase Request"),
            ("purchase.order", "Purchase Order"),
            ("budget.commitment", "Budget Commitment"),
            ("budget.move", "Budget Move"),
            ("account.move.request", "Account Move Request"),
            ("account.move", "Account Move"),
        ],
        string="Reference Type",
        required=True,
    )
    res_id = fields.Integer(
        string="Reference ID",
        required=True,
    )
    res_name = fields.Char(
        string="Reference Name",
        compute="_compute_res_name",
        store=True,
    )

    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        for record in self:
            if record.res_model and record.res_id:
                try:
                    ref_record = self.env[record.res_model].browse(record.res_id)
                    if ref_record.exists():
                        record.res_name = ref_record.display_name
                    else:
                        record.res_name = False
                except Exception:
                    record.res_name = False
            else:
                record.res_name = False

    def action_view_reference(self):
        """Open the referenced record"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }
