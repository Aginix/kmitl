# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin", "thai.date.mixin"]
    _inherits = {"purchase.request": "request_id"}

    _description = "Purchase Request Approval"
    _order = "date desc, name desc"
    _check_company_auto = True

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("purchase.request.approval")

    # == Business fields ==
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        required=True,
        readonly=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )

    name = fields.Char(
        string="Approval Reference",
        required=True,
        default=lambda self: _("New"),
        tracking=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("to_approve", "To be approved"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        readonly=True,
        index=True,
    )

    date = fields.Datetime("Date", default=fields.Datetime.now, tracking=True)
    approval_date = fields.Datetime("Approval Date", tracking=True)

    origin = fields.Char(string="Source Document")

    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        tracking=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_request.group_purchase_request_manager").id,
            )
        ],
        index=True,
    )

    # department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    # requesting_department_id = fields.Many2one('hr.department', string='Department', tracking=True)

    report_html_url = fields.Char(compute="_compute_report_html_url")

    _sql_constraints = [
        (
            "request_id_uniq",
            "unique(request_id)",
            _("A purchase approval already exists!"),
        )
    ]

    def button_draft(self):
        return self.write({"state": "draft"})

    def button_to_approve(self):
        for rec in self:
            rec.state = "to_approve"
            rec.name = (
                rec.name
                or self.env["ir.sequence"].next_by_code("purchase.request.approval")
                or _("New")
            )

    def _message_link_back_to_request(self):
        request_id = self.request_id
        name = request_id.name
        link = request_id._get_record_url()

        return _(
            'This record has been created from: <a href="%(link)s" target="_blank">%(name)s</a>',
            link=link,
            name=name,
        )

    def button_approved(self):
        for rec in self:
            message = rec.request_id._purchase_request_approval_approved_message_content(rec)
            rec.request_id.message_post(body=message, message_type="comment")
            rec.request_id.activity_schedule(
                    "purchase_request_activity_kmitl.mail_activity_create_purchase_order",
                    user_id=rec.request_id.user_id.id,
                    # note=_("Your activity is going to end soon"),
                )
            rec.write({"state": "approved", "approval_date": fields.Datetime.now()})

    def button_rejected(self):
        for rec in self:
            message = rec.request_id._purchase_request_reject_approved_message_content(rec)
            rec.request_id.message_post(body=message, message_type="comment")
            rec.write({"state": "rejected"})

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update({"state": "draft", "name": self._get_default_name()})
        return super().copy(default)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._get_default_name()
        requests = super().create(vals_list)
        return requests

    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for rec in self:
            if not rec._can_be_deleted():
                raise UserError(
                    _("You cannot delete a purchase approval which is not draft.")
                )
        return super().unlink()

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/purchase_request_approval/{request.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return "PA - %s" % (self.name)

    def open_preview(self):
        if self.id:
            return {
                "type": "ir.actions.act_url",
                "url": self.access_url,
                "target": "new",
            }

    @api.depends("state")
    def _compute_report_html_url(self):
        for rec in self:
            rec.report_html_url = rec.get_portal_url(report_type='html')

    def action_view_request(self):
        self.ensure_one()
        action = self.env.ref("purchase_request.purchase_request_form_action").sudo().read()[0]
        form = self.env.ref("purchase_request.view_purchase_request_form")
        action["views"] = [(form.id, "form")]
        action["res_id"] = self.request_id.id
        return action
