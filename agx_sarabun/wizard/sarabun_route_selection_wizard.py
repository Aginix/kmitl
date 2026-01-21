# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SarabunRouteSelectionWizard(models.TransientModel):
    """Wizard to select route template when multiple templates match"""

    _name = "sarabun.route.selection.wizard"
    _description = "Route Selection Wizard"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
    )
    available_template_ids = fields.Many2many(
        comodel_name="sarabun.route.template",
        string="Available Routes",
    )
    selected_template_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Selected Route",
        required=True,
        domain="[('id', 'in', available_template_ids)]",
    )

    # Display info
    origin_info = fields.Char(
        string="Origin",
        compute="_compute_origin_info",
    )

    @api.depends("document_id")
    def _compute_origin_info(self):
        for record in self:
            if record.document_id.origin_model and record.document_id.origin_res_id:
                try:
                    origin = record.document_id.env[record.document_id.origin_model].browse(
                        record.document_id.origin_res_id
                    )
                    if origin.exists():
                        record.origin_info = "{}: {}".format(
                            origin._description, origin.display_name
                        )
                    else:
                        record.origin_info = ""
                except Exception:
                    record.origin_info = ""
            else:
                record.origin_info = ""

    def action_confirm(self):
        """Apply selected template to document"""
        self.ensure_one()
        self.document_id._apply_route_template(self.selected_template_id)
        return {"type": "ir.actions.act_window_close"}
