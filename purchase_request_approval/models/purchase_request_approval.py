# -*- coding: utf-8 -*-
import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "portal.mixin",
        "thai.date.mixin",
        "tier.validation",
        "sarabun.document.mixin",
    ]

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

    requesting_department_id = fields.Many2one(
        "hr.department", string="Department", tracking=True
    )

    report_html_url = fields.Char(compute="_compute_report_html_url")

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )

    # == Own fields (copied from purchase.request on creation) ==
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
    )
    estimated_cost = fields.Float(string="Estimated Cost")
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
    )
    line_ids = fields.One2many(
        comodel_name="purchase.request.approval.line",
        inverse_name="approval_id",
        string="Lines",
    )

    # == Related fields (read-through to purchase.request) ==
    title = fields.Char(related="request_id.title")
    description = fields.Text(related="request_id.description")
    requested_by = fields.Many2one(related="request_id.requested_by")
    department_id = fields.Many2one(related="request_id.department_id")
    company_id = fields.Many2one(related="request_id.company_id", store=True)
    partner_id = fields.Many2one(related="request_id.partner_id")
    user_id = fields.Many2one(related="request_id.user_id")
    product_id = fields.Many2one(related="request_id.product_id")
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount_total = fields.Monetary(related="request_id.amount_total")
    amount_untaxed = fields.Monetary(related="request_id.amount_untaxed")
    amount_tax = fields.Monetary(related="request_id.amount_tax")
    source_analytic_id = fields.Many2one(related="request_id.source_analytic_id")
    budget_account_id = fields.Many2one(related="request_id.budget_account_id")
    budget_commitment_id = fields.Many2one(related="request_id.budget_commitment_id")
    analytic_distribution = fields.Json(related="request_id.analytic_distribution")
    attachment_ids = fields.One2many(related="request_id.attachment_ids")
    work_acceptance_committee_ids = fields.One2many(
        related="request_id.work_acceptance_committee_ids"
    )
    tor_committee_ids = fields.One2many(related="request_id.tor_committee_ids")
    price_determine_committee_ids = fields.One2many(
        related="request_id.price_determine_committee_ids"
    )
    evaluation_committee_ids = fields.One2many(
        related="request_id.evaluation_committee_ids"
    )

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
        self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
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
        for rec in self:
            if (
                rec.main_sarabun_document_id
                and rec.main_sarabun_document_id.state == "sent"
            ):
                raise UserError(
                    _(
                        "Cannot manually approve while Sarabun routing is pending. "
                        "Please wait for the routing to complete or cancel the Sarabun document."
                    )
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
            message = (
                rec.request_id._purchase_request_approval_rejected_message_content(rec)
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
        if not self.env.user.has_group(
            "purchase_request.group_purchase_request_manager"
        ):
            raise UserError(
                _("You do not have permission to delete purchase approvals.")
            )
        for rec in self:
            if not rec._can_be_deleted():
                raise UserError(
                    _("You cannot delete a purchase approval which is not draft.")
                )
        return super().unlink()

    def _compute_access_url(self):
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

    def button_validate(self):
        self.ensure_one()
        self.write({"state": "validate"})
        self.message_post(body=_("Document validated and ready for routing."))

    def _prepare_sarabun_document_vals(self):
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.title or self.name
        if self.requesting_department_id:
            vals["sender_department_id"] = self.requesting_department_id.id
        return vals

    def action_submit_to_sarabun(self):
        self.ensure_one()

        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))

        self.main_sarabun_document_id = document

        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _on_sarabun_sent(self, document):
        _logger.info(
            "Sarabun sent callback for PA %s (id=%s) from document %s",
            self.name,
            self.id,
            document.name,
        )
        self.write({"state": "to_approve"})
        self.message_post(
            body=_("Sent for approval via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_completed(self, document):
        _logger.info(
            "Sarabun completed callback for PA %s (id=%s) from document %s",
            self.name,
            self.id,
            document.name,
        )
        self.button_approved()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, recipient):
        _logger.info(
            "Sarabun rejected callback for PA %s (id=%s) from document %s",
            self.name,
            self.id,
            document.name,
        )
        self.button_rejected()
        reason = recipient.comment if recipient else _("No reason provided")
        self.message_post(
            body=_("Rejected via Sarabun. Reason: %s") % reason,
        )

    def _get_sarabun_report_action(self):
        return self.env.ref(
            "purchase_request_approval.action_report_purchase_request_approvals"
        )
