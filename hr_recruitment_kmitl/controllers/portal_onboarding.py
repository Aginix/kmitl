# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class PortalOnboardingController(http.Controller):

    @http.route(['/my/onboarding'], type='http', auth='user', website=True)
    def portal_my_onboarding_list(self, **kwargs):
        return request.render('hr_recruitment_kmitl.portal_my_onboarding_list', {})

    @http.route(['/my/onboarding/<int:onboarding_id>'], type='http', auth='user', website=True)
    def portal_my_onboarding_detail(self, onboarding_id, **kwargs):
        return request.render('hr_recruitment_kmitl.portal_my_onboarding_detail', {})

    @http.route(['/my/onboarding/form/<int:onboarding_id>'], type='http', auth='user', website=True)
    def portal_my_onboarding_form(self, onboarding_id, **kwargs):
        return request.render('hr_recruitment_kmitl.portal_my_onboarding_form', {})