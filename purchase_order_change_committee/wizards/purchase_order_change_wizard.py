# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = 'purchase.order.change.wizard'
    _description = _('Purchase Order ChangeWizard')

    show_committee = fields.Boolean()
    work_acceptance_committee_ids_old = fields.Many2many(
        comodel_name="procurement.committee",
        relation="purchase_change_wizard_committee_old_rel",
        column1="wizard_id",
        column2="committee_id",
        string="Old Committee",
        readonly=True,
    )

    work_acceptance_committee_ids = fields.Many2many(
        comodel_name="procurement.committee",
        relation="purchase_change_wizard_committee_new_rel",
        column1="wizard_id",
        column2="committee_id",
        string="New Committee",
    )

    def _prepare_old_values(self, purchase):
        vals = super()._prepare_old_values(purchase)

        committees = purchase.work_acceptance_committee_ids

        vals["work_acceptance_committee_ids_old"] = [
            (6, 0, committees.ids)
        ]

        return vals

    def _prepare_section_visibility(self, section_xml_ids):
            vals = super()._prepare_section_visibility(section_xml_ids)
            vals["show_committee"] = "purchase_change_section_4" in section_xml_ids
            return vals

    def _save_committee_changes(self):
        po = self.purchase_id.sudo()

        if self.work_acceptance_committee_ids:
            po.write({
                "work_acceptance_committee_ids": [
                    (6, 0, self.work_acceptance_committee_ids.ids)
                ]
            })

    def action_save_changes(self):
        res = super().action_save_changes()
        self._save_committee_changes()
        return res
