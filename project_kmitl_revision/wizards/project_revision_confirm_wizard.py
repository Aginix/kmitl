import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class ProjectRevisionConfirmWizard(models.TransientModel):
    _name = "project.revision.confirm.wizard"
    _description = _("ProjectRevisionConfirmWizard")

    project_id = fields.Many2one("project.project", required=True)

    def confirm_create_revision(self):
        self.ensure_one()
        return self.project_id.create_revision()
