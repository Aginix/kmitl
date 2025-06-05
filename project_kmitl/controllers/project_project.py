from odoo import http
from odoo.http import request


class ProjectProject(http.Controller):
    @http.route(['/projects/<int:project_id>'], type='http', auth='public', website=True)
    def project_public_view(self, project_id, **kwargs):
        project = request.env['project.project'].sudo().browse(project_id)
        if not project.exists():
            return request.not_found()
        return request.render('project_kmitl.public_project_template', {
            'project': project
        })
