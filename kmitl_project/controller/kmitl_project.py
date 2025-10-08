
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, Response
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

class KmitlProjectPortal(portal.CustomerPortal):
    @http.route(['/my/kmitl-project/<int:kmitl_project_id>'], type='http', auth="public", website=True)
    def portal_my_kmitl_project(self, kmitl_project_id=None, access_token=None, **kw):
        try:
            project_sudo = self._document_check_access('kmitl.project', kmitl_project_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._get_page_view_values(project_sudo, access_token, { 'kmitl_project': project_sudo }, "my_kmitl_projects_history", False, **kw)
        return request.render("kmitl_project.portal_my_kmitl_project", values)
