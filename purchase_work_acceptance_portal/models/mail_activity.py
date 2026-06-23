# -*- coding: utf-8 -*-
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_todo_action_links(self):
        """Add portal WA + portal PO links for committee review Todos.

        Token-aware: resolves the recipient's own ``committee_token`` so the
        URL works without backend login.
        """
        links = super()._get_todo_action_links()
        self.ensure_one()
        if self.res_model != "work.acceptance" or not self.user_id:
            return links
        wa = self.env["work.acceptance"].browse(self.res_id).exists()
        if not wa:
            return links
        committee = wa.work_acceptance_committee_ids.filtered(
            lambda c: c.employee_id.user_id == self.user_id
        )[:1]
        if not committee:
            return links
        wa_url = "%s&committee_token=%s" % (
            wa.get_portal_link(),
            committee.access_token,
        )
        links.append({
            "label": "ตรวจรับใน Portal",
            "url": wa_url,
            "icon": "fa-external-link",
        })
        if wa.purchase_id:
            order_url = "%s&wa_token=%s" % (
                wa.purchase_id.get_portal_link(),
                wa.access_token,
            )
            links.append({
                "label": "เอกสารสัญญา (PO)",
                "url": order_url,
                "icon": "fa-file-text-o",
            })
        return links
