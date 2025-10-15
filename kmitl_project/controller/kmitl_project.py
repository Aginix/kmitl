# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class KmitlProjectPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'project_count' in counters:
            values['project_count'] = request.env['kmitl.project'].sudo().search_count([])
        return values

    @http.route(['/my/kmitl-projects', '/my/kmitl-projects/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_kmitl_projects(self, page=1, **kw):
        """Display list of KMITL Projects"""
        values = self._prepare_portal_layout_values()
        KmitlProject = request.env['kmitl.project'].sudo()

        # Simple domain - just show all projects
        domain = []
        projects_count = KmitlProject.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/kmitl-projects",
            total=projects_count,
            page=page,
            step=self._items_per_page
        )

        # Fetch records
        projects = KmitlProject.search(domain, order='id desc', limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'projects': projects,
            'page_name': 'kmitl_projects',
            'pager': pager,
            'default_url': '/my/kmitl-projects',
        })

        return request.render("kmitl_project.portal_my_kmitl_projects", values)

    @http.route(['/my/kmitl-project/<int:project_id>'], type='http', auth="public", website=True)
    def portal_my_kmitl_project(self, project_id=None, access_token=None, **kw):
        """Display single KMITL Project detail"""
        try:
            project_sudo = self._document_check_access('kmitl.project', project_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._get_page_view_values(project_sudo, access_token, {'kmitl_project': project_sudo}, False, False, **kw)

        return request.render("kmitl_project.portal_my_kmitl_project", values)
