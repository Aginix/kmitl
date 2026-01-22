# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = 'purchase.order.change.wizard'
    _description = _('Purchase Order ChangeWizard')

    show_committee = fields.Boolean()
    work_acceptance_committee_ids = fields.One2many(comodel_name="procurement.committee")

    def _prepare_old_values(self, purchase):
        vals = super()._prepare_old_values(purchase)

        committees = purchase.work_acceptance_committee_ids

        vals["work_acceptance_committee_ids"] = [
            (6, 0, committees.ids)
        ]

        return vals

    def _prepare_section_visibility(self, section_xml_ids):
            vals = super()._prepare_section_visibility(section_xml_ids)
            vals["show_committee"] = "purchase_change_section_4" in section_xml_ids
            return vals

    def _get_track_fields(self):
        track_fields = super()._get_track_fields()

        track_fields.update({
            "work_acceptance_committee_ids": "คณะกรรมการตรวจรับพัสดุ",
        })

        return track_fields
