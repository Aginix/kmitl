# -*- coding: utf-8 -*-
from odoo import models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "portal.mixin"]

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/purchase_request/{request.id}"

    def get_portal_url(self, suffix=None, report_type=None, **kwargs):
        """
        Get the portal URL for this purchase request.

        Args:
            report_type: 'html' or 'pdf' to generate report URL
            suffix: Additional URL suffix
        """
        self.ensure_one()
        url = self.access_url
        if report_type:
            url = f"{url}/{report_type}"
        if suffix:
            url = f"{url}{suffix}"
        if kwargs.get("query_string"):
            url = f"{url}?{kwargs['query_string']}"
        return url
