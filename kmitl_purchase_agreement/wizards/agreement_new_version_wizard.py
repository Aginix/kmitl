# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AgreementNewVersionWizard(models.TransientModel):
    _name = 'agreement.new.version.wizard'
    _description = 'Agreement New Version Wizard'

    name = fields.Char(string="Name")
    agreement_id = fields.Many2one("agreement", string="Agreement", required=True)
    attachment_ids = fields.One2many(
        comodel_name="agreement.wizard.attachment",
        inverse_name="wizard_id",
        string="Attachments",
    )
    # verify_datetime = fields.Date(string="Date of Verification")

    def action_confirm(self):
        self.ensure_one()
        agreement = self.agreement_id

        for attach in self.attachment_ids:
            self.env["purchase.agreement.attachment"].create({
                "request_id": agreement.id,
                "name": attach.name,
                "file_name": attach.file_name,
                "file": attach.file,
                "description": attach.description,
            })

        # if self.verify_datetime:
        #     agreement.verify_datetime = self.verify_datetime

        agreement.create_new_version()
        return {"type": "ir.actions.act_window_close"}

