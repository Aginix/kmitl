# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = 'purchase.order.change.wizard'
    _description = _('Purchase Order ChangeWizard')

    show_invoice = fields.Boolean()

    invoice_plan_ids_old = fields.Many2many(
        comodel_name="purchase.invoice.plan",
        relation="purchase_change_wizard_invoice_old_rel",
        column1="wizard_id",
        column2="invoice_plan_id",
        string="Old Invoice Plan",
        readonly=True,
    )

    invoice_plan_ids = fields.Many2many(
        comodel_name="purchase.invoice.plan",
        relation="purchase_change_wizard_invoice_new_rel",
        column1="wizard_id",
        column2="invoice_plan_id",
        string="New Invoice Plan",
        readonly=True,
    )

    def _prepare_old_values(self, purchase):
        vals = super()._prepare_old_values(purchase)

        invoice_plans = purchase.invoice_plan_ids

        vals["invoice_plan_ids_old"] = [
            (6, 0, invoice_plans.ids)
        ]

        return vals

    def _prepare_section_visibility(self, section_xml_ids):
        _logger.warning("SECTION XML IDS >>> %s", section_xml_ids)
        vals = super()._prepare_section_visibility(section_xml_ids)
        vals["show_invoice"] = "purchase_change_section_5" in section_xml_ids
        return vals

    def _get_track_fields(self):
        fields = super()._get_track_fields()
        fields.update({
            "invoice_plan_ids": "งวดงาน"
        })
        return fields

    def _save_invoice_changes(self):
        po = self.purchase_id.sudo()

        if self.invoice_plan_ids:
            commands = [(6, 0, self.invoice_plan_ids.ids)]
        else:
            commands = [(5, 0, 0)]

        po.write({
            "invoice_plan_ids": commands
        })

    def action_save_changes(self):
        res = super().action_save_changes()
        self._save_invoice_changes()
        return res
