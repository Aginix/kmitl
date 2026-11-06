from odoo import models


class KmitlProject(models.Model):
    """Projects take Change requests: whoever checks a project details what
    to fix as requests, and a project officer may close one on its author's
    behalf. They never hold up the project."""

    _name = "kmitl.project"
    _inherit = ["kmitl.project", "change.request.mixin"]

    def _change_request_can_close_on_behalf(self):
        self.ensure_one()
        return self.env.user.has_group("kmitl_project.group_kmitl_project_user_all")
