# -*- coding: utf-8 -*-
from odoo import models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _notify_review_requested(self, tier_reviews):
        # Suppress OCA's default subscribe/message_post. Todo scheduling and
        # clearing are handled by the base.automation records in
        # data/base_automation.xml.
        return
