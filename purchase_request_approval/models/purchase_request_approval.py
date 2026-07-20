# -*- coding: utf-8 -*-
import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin", "thai.date.mixin", "tier.validation", "sarabun.document.mixin"]
    _inherits = {"purchase.request": "request_id"}

    _description = "Purchase Request Approval"
    _order = "date_start desc, name desc"
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
            ("reject", "Rejected"),
            ("cancel", "Cancel"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        readonly=True,
        index=True,
    )

    date_start = fields.Date(copy=False)
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

    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )

    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )

    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
    )

    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )

    requesting_department_id = fields.Many2one('hr.department', string='Department', tracking=True)

    report_html_url = fields.Char(compute="_compute_report_html_url")

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )

    # _sql_constraints = [
    #     (
    #         "request_id_uniq",
    #         "unique(request_id)",
    #         _("A purchase approval already exists!"),
    #     )
    # ]

    def button_draft(self):
        return self.write({"state": "draft"})

    def button_to_approve(self):
        for rec in self:
            rec.state = "to_approve"
            rec.report_generate()
            rec.name = (
                rec.name
                or self.env["ir.sequence"].next_by_code("purchase.request.approval")
                or _("New")
            )

    def report_generate(self):
        self.ensure_one()

        report = self.env["ir.actions.report"]._render_qweb_pdf(
            "purchase_request_approval.report_purchase_request_approval",
            [self.id],
        )
        filename = self.name + ".pdf"
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                # "raw": base64.b64encode(report[0]),
                "datas": base64.b64encode(report[0]),
                "type": "binary",
                "mimetype": "application/pdf",
            }
        )

        self.message_post(
            body=(_("PA Report is generated on %s") % fields.Datetime.now())
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
        # Check if sarabun routing is pending
        for rec in self:
            if rec.main_sarabun_document_id and rec.main_sarabun_document_id.state == "sent":
                raise UserError(
                    _("Cannot manually approve while Sarabun routing is pending. "
                      "Please wait for the routing to complete or cancel the Sarabun document.")
                )
        for rec in self:
            message = (
                rec.request_id._purchase_request_approval_approved_message_content(rec)
            )
            rec.request_id.message_post(body=message, message_type="comment")
            rec._activity_awaiting_create_purchase_order()
            rec.write({"state": "approved", "approval_date": fields.Datetime.now()})
            if rec.request_id and rec.request_id.state == "in_approval":
                rec.request_id.write({"state": "in_progress"})

    def _activity_awaiting_create_purchase_order(self):
        self.request_id.activity_schedule(
            "mail_activity_create_purchase_order",
            user_id=self.request_id.user_id.id,
        )

    def button_cancel(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ยกเลิกใบขออนุมัติ (พจ.1)"),
            "res_model": "purchase.request.approval.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_id": self.id},
        }

    def button_reject(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับใบขออนุมัติ (พจ.1)"),
            "res_model": "purchase.request.approval.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_id": self.id},
        }

    def _action_do_cancel(self, reason):
        self.ensure_one()
        pa_body = _(
            "ยกเลิกใบขออนุมัติ (พจ.1) %(pa)s เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.message_post(body=pa_body, subtype_xmlid="mail.mt_note")
        pr_body = self.request_id._purchase_request_approval_cancelled_message_content(
            self
        )
        pr_body += "<br/>%s" % (_("เหตุผล: %s") % reason)
        self.request_id.message_post(body=pr_body, subtype_xmlid="mail.mt_note")
        self.write({"state": "cancel"})
        if self.request_id:
            self.request_id.button_cancel()

    def _action_do_return(self, reason):
        self.ensure_one()
        pa_body = _(
            "ตีกลับใบขออนุมัติ (พจ.1) %(pa)s เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.message_post(body=pa_body, subtype_xmlid="mail.mt_note")
        pr_body = _(
            "ใบขออนุมัติ (พจ.1) %(pa)s ถูกตีกลับ เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.request_id.message_post(
            body='<span class="text-warning">%s</span>' % pr_body,
            subtype_xmlid="mail.mt_note",
        )
        self.button_draft()

    def _action_do_reject(self, reason):
        self.ensure_one()
        pa_body = _(
            "ปฎิเสธใบขออนุมัติ (พจ.1) %(pa)s เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.message_post(body=pa_body, subtype_xmlid="mail.mt_note")
        pr_body = self.request_id._purchase_request_approval_rejected_message_content(
            self
        )
        pr_body += "<br/>%s" % (_("เหตุผล: %s") % reason)
        self.request_id.message_post(body=pr_body, subtype_xmlid="mail.mt_note")
        self.write({"state": "reject"})
        if self.request_id:
            self.request_id.button_rejected()

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
        if not self.env.user.has_group("purchase_request.group_purchase_request_manager"):
            raise UserError(_("You do not have permission to delete purchase approvals."))
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
            rec.report_html_url = rec.get_portal_url(report_type="html")

    def action_view_request(self):
        self.ensure_one()
        action = (
            self.env.ref("purchase_request.purchase_request_form_action")
            .sudo()
            .read()[0]
        )
        form = self.env.ref("purchase_request.view_purchase_request_form")
        action["views"] = [(form.id, "form")]
        action["res_id"] = self.request_id.id
        return action

    # === Sarabun Document Integration ===

    def _prepare_sarabun_document_vals(self):
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.title or self.name
        if self.requesting_department_id:
            vals["sender_department_id"] = self.requesting_department_id.id
        return vals

    def action_submit_to_sarabun(self):
        """Submit PA to Sarabun for approval routing."""
        self.ensure_one()

        # Create sarabun document
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))

        # Link to PA
        self.main_sarabun_document_id = document

        # Log to chatter
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )

        # Open sarabun document form for routing selection
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _on_sarabun_sent(self, document):
        """
        Called when sarabun document is sent (routing started).
        Changes PA state to 'to_approve'.
        """
        _logger.info(
            "Sarabun sent callback for PA %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        self.write({"state": "to_approve"})
        self.message_post(
            body=_("Sent for approval via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_completed(self, document):
        """
        Called when sarabun document routing is completed.
        Auto-approves the PA.
        """
        _logger.info(
            "Sarabun completed callback for PA %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        self.button_approved()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, recipient):
        """
        Called when sarabun document is rejected.
        Cancels the PA and cascades cancel to the parent PR.
        """
        _logger.info(
            "Sarabun rejected callback for PA %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        reason = recipient.comment if recipient else _("No reason provided")
        self._action_do_reject(reason)

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request Approval report."""
        return self.env.ref(
            "purchase_request_approval.action_report_purchase_request_approvals"
        )
