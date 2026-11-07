from odoo.http import request
from odoo.osv import expression

from odoo.addons.kmitl_project_portal.controllers.portal import KmitlProjectPortal


class KmitlProjectCoordinatorPortal(KmitlProjectPortal):
    def _get_project_domain(self):
        # The coordinator is a project owner too — list coordinated projects.
        return expression.OR(
            [
                super()._get_project_domain(),
                [("coordinator_ids", "in", request.env.user.id)],
            ]
        )
