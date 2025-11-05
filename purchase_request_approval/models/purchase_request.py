# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    hide_create_approval_button = fields.Boolean(
        compute="_compute_hide_create_approval_button"
    )
    request_approval_count = fields.Integer(compute="_compute_request_approval_count")
    request_approval_ids = fields.One2many(
        "purchase.request.approval", inverse_name="request_id"
    )

    def _prepare_approval_vals(self):
        return {
            "request_id": self.id,
            "origin": self.name,
            "message_main_attachment_id": self.message_main_attachment_id.id,
        }

    def button_create_approval(self):
        self.ensure_one()

        exists = self.env["purchase.request.approval"].search(
            [("request_id", "=", self.id)], limit=1
        )

        if exists:
            raise UserError(_("Purchase Request Approval has already been created"))

        approval = self.env["purchase.request.approval"].create(
            self._prepare_approval_vals()
        )

        link_back_message = approval._message_link_back_to_request()
        approval.message_post(body=link_back_message, message_type="comment")

        message = self._purchase_request_approval_create_message_content(approval)
        self.message_post(body=message, message_type="comment")

    def _purchase_request_approval_create_message_content(self, approval):
        message = _(
            "Purchase approval %(pa_name)s for your Request %(pr_name)s created successfully, waiting for operation."
        ) % {
            "pr_name": self.name,
            "pa_name": approval.name,
        }

        return message

    def _purchase_request_approval_approved_message_content(self, approval):
        message = _("Purchase approval %(pa_name)s was successfully approved 👍.") % {
            "pa_name": approval.name,
            "pa_name": approval.name,
        }
        return message

    def _purchase_request_approval_rejected_message_content(self, approval):
        title = _(
            "Purchase approval %(pa_name)s for your Request %(pr_name)s has been rejected 👎."
        ) % {
            "pr_name": self.name,
            "pa_name": approval.name,
        }
        message = '<span class="text-danger">%s</span>' % title
        return message

    @api.depends("state", "estimated_cost", "request_approval_count")
    def _compute_hide_create_approval_button(self):
        for rec in self:
            if rec.request_approval_count > 0:
                rec.hide_create_approval_button = True
            elif rec.state in ("approved") and rec.estimated_cost <= 100000:
                rec.hide_create_approval_button = False
            else:
                rec.hide_create_approval_button = True

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)

    def action_view_request_approval(self):
        self.ensure_one()
        action = (
            self.env.ref("purchase_request_approval.action_purchase_request_approval")
            .sudo()
            .read()[0]
        )

        if len(self.request_approval_ids) > 1:
            action["domain"] = [("id", "in", self.request_approval_ids.ids)]
        elif self.request_approval_ids:
            form_view = [
                (
                    self.env.ref(
                        "purchase_request_approval.view_purchase_request_approval_form"
                    ).id,
                    "form",
                )
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = self.request_approval_ids.id

        action["domain"] = [("request_id", "=", self.id)]
        return action

    @api.depends("request_approval_ids")
    def _compute_request_approval_count(self):
        for rec in self:
            rec.request_approval_count = len(rec.request_approval_ids)

    def _hide_create_po_button(self):
        super()._hide_create_po_button()
        for rec in self:
            if (
                rec.state in ("approved", "in_progress")
                and rec.purchase_count == 0
                and rec.estimated_cost <= 100000
            ):
                if rec.request_approval_ids.state in ('approved'):
                    rec.hide_create_po_button = False
                else:
                    rec.hide_create_po_button = True
