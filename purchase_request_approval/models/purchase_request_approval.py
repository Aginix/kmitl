# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
            ("validate", "Validate"),
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
            document = rec.active_sarabun_document_id
            if document and document.is_circulating:
                raise UserError(
                    _("Cannot manually approve while the หนังสือ is still circulating. "
                      "Please wait for the routing to complete or recall the Sarabun document.")
                )
        for rec in self:
            message = (
                rec.request_id._purchase_request_approval_approved_message_content(rec)
            )
            rec.request_id.message_post(body=message, message_type="comment")
            rec._activity_awaiting_create_purchase_order()
            rec.write({"state": "approved", "approval_date": fields.Datetime.now()})

    def _activity_awaiting_create_purchase_order(self):
        self.request_id.activity_schedule(
            "mail_activity_create_purchase_order",
            user_id=self.request_id.user_id.id,
        )

    def button_rejected(self):
        for rec in self:
            message = rec.request_id._purchase_request_approval_rejected_message_content(
                rec
            )
            rec.request_id.message_post(body=message, message_type="comment")
            rec.write({"state": "rejected"})
            if rec.request_id:
                rec.request_id.button_rejected()

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

    @api.depends("state")
    def _compute_is_editable(self):
        """Override to make validate state non-editable."""
        super()._compute_is_editable()
        for record in self:
            if record.state in ("validate", "to_approve", "approved", "rejected"):
                record.is_editable = False

    # === Sarabun Document Integration ===

    def button_validate(self):
        """Move to validate state for data confirmation before routing."""
        self.ensure_one()
        self.write({"state": "validate"})
        self.message_post(body=_("Document validated and ready for routing."))

    def _get_sarabun_subject(self):
        return self.title or self.name

    def _get_sarabun_sender_department(self):
        return self.requesting_department_id or super()._get_sarabun_sender_department()

    def _on_sarabun_circulating(self, document):
        # Explicit override: flip the PA to 'to_approve' on send. Do NOT call
        # button_to_approve here — that also renders the PDF and assigns the name.
        self.write({"state": "to_approve"})
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # Routing completed → auto-approve the PA.
        self.button_approved()
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        # ปฏิเสธ (terminal) → PA rejected.
        self.button_rejected()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        # ตีกลับ / ดึงกลับ (revisable) → back to 'validate' to amend & re-submit.
        self.write({"state": "validate"})
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง (terminal) → back to 'draft' so it can be re-opened.
        self.write({"state": "draft"})
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request Approval report."""
        return self.env.ref(
            "purchase_request_approval.action_report_purchase_request_approvals"
        )
