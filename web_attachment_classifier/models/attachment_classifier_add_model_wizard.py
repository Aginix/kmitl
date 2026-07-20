from odoo import fields, models


class AttachmentClassifierAddModelWizard(models.TransientModel):
    """Two-step "Add Model" flow used by the Attachment Doctypes tree.

    The primary settings view lists `ir.model` records filtered to those
    that already have Mappings, with `create="false"` so a user can't
    accidentally create a manual ir.model (Studio-style side effects).
    To let them add a new model to the configuration we route through
    this wizard: user picks an *existing* ir.model, then we open that
    model's form (in our custom view) where they add the doctype rows.
    """

    _name = "attachment.classifier.add.model.wizard"
    _description = "Add Attachment Doctype Model"

    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
    )

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.model",
            "res_id": self.res_model_id.id,
            "view_mode": "form",
            "view_id": self.env.ref(
                "web_attachment_classifier.view_ir_model_classifier_form"
            ).id,
            "target": "current",
        }
