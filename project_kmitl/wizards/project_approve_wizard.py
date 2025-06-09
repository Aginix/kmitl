import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class ProjectApproveWizard(models.TransientModel):
    _name = "project.approve.wizard"
    _description = _("ProjectApproveWizard")

    office_order_no = fields.Char(string="เลขที่หนังสืออนุมัติจากระบบ e-office", required=True)
    project_id = fields.Many2one(
        "project.project", string="Project", readonly=True, required=True
    )

    def confirm_approve(self):
        self.ensure_one()
        old_revisions = self.env["project.project"].search(
            [("current_revision_id", "=", self.project_id.id)]
        )
        old_revisions.write({"state": "revised"})
        self.project_id.write(
            {
                "office_order_no": self.office_order_no,
                "reference": self.env["ir.sequence"].next_by_code("project.project"),
                "state": "approve",
            }
        )
