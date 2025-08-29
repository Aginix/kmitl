from odoo import _, api, fields, models


class AgreementWizardAttachment(models.TransientModel):
    _name = "agreement.wizard.attachment"
    _description = "Temporary Attachments for Agreement Wizard"

    name = fields.Char("Name")
    file = fields.Binary("File", required=True)
    file_name = fields.Char("Filename")
    description = fields.Char("Description")
    wizard_id = fields.Many2one(
        "agreement.new.version.wizard", string="Wizard", ondelete="cascade"
    )
