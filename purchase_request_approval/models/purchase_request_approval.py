# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
            ("to_approve", "To be approved"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("sarabun_returned", "Sarabun Returned"),
            ("pending_pr", "Pending PR Revision"),
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
    title = fields.Char(string="Title")
    description = fields.Text(string="Description")
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
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        store=True,
        readonly=True,
        compute="_amount_all",
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
    )
    line_ids = fields.One2many(
        comodel_name="purchase.request.approval.line",
        inverse_name="approval_id",
        string="Lines",
    )

    # == Related fields (read-through to purchase.request) ==
    # Note: `title` and `description` are PA-own copied fields (per ADR-0004);
    # they used to be re-declared as `related=request_id.*` here, which
    # accidentally shadowed the own declarations above and prevented PA-side
    # divergence. Removed to restore ADR-0004 intent.
    requested_by = fields.Many2one(related="request_id.requested_by")
    department_id = fields.Many2one(related="request_id.department_id", store=True)
    company_id = fields.Many2one(related="request_id.company_id", store=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        tracking=True,
    )
    vat_included = fields.Selection(
        [("exclusive", "VAT Exclusive"), ("inclusive", "VAT Inclusive")],
        default="exclusive",
        tracking=True,
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        domain="[('type_tax_use', 'in', ['purchase']), ('company_id', '=', company_id)]",
        check_company=True,
        context={"active_test": False},
    )

    @api.onchange("vat_included")
    def _onchange_vat_included(self):
        if self.vat_included == "inclusive":
            if self.tax_id:
                return
            default_tax = self.env["account.tax"].search(
                [
                    ("type_tax_use", "in", ["purchase"]),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            self.tax_id = default_tax.id
        else:
            self.tax_id = False

    user_id = fields.Many2one(related="request_id.user_id")
    product_id = fields.Many2one(related="request_id.product_id")
    currency_id = fields.Many2one(related="request_id.currency_id")
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        store=True,
        readonly=True,
        compute="_amount_all",
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        store=True,
        readonly=True,
        compute="_amount_all",
    )
    amount_total = fields.Monetary(
        string="Total",
        store=True,
        readonly=True,
        compute="_amount_all",
    )
    tax_totals = fields.Binary(compute="_compute_tax_totals", exportable=False)
    source_analytic_id = fields.Many2one(related="request_id.source_analytic_id")
    budget_account_id = fields.Many2one(related="request_id.budget_account_id")
    budget_commitment_id = fields.Many2one(related="request_id.budget_commitment_id")
    analytic_distribution = fields.Json(related="request_id.analytic_distribution")
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Document Attachments",
        domain=[("res_model", "=", "purchase.request.approval")],
        auto_join=True,
    )
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

    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state in ("draft", "sarabun_returned")

    @api.depends("line_ids.price_total")
    def _amount_all(self):
        for record in self:
            line_ids = record.line_ids
            if record.company_id.tax_calculation_rounding_method == "round_globally":
                tax_results = self.env["account.tax"]._compute_taxes(
                    [line._convert_to_tax_base_line_dict() for line in line_ids]
                )
                totals = tax_results["totals"]
                amount_untaxed = (
                    totals.get(record.currency_id, {}).get("amount_untaxed", 0.0)
                )
                amount_tax = (
                    totals.get(record.currency_id, {}).get("amount_tax", 0.0)
                )
            else:
                amount_untaxed = sum(line_ids.mapped("price_subtotal"))
                amount_tax = sum(line_ids.mapped("price_tax"))
            record.amount_untaxed = amount_untaxed
            record.amount_tax = amount_tax
            record.amount_total = amount_untaxed + amount_tax
            record.estimated_cost = amount_untaxed + amount_tax

    @api.depends_context("lang")
    @api.depends(
        "line_ids.tax_id",
        "line_ids.price_subtotal",
        "amount_total",
        "amount_untaxed",
    )
    def _compute_tax_totals(self):
        for record in self:
            line_ids = record.line_ids
            record.tax_totals = self.env["account.tax"]._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in line_ids],
                record.currency_id or record.company_id.currency_id,
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

    def action_open_material_withdrawal_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("พิมพ์ใบเบิกวัสดุ (พ.43)"),
            "res_model": "purchase.request.approval.material.withdrawal.wizard",
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
        self.write({"state": "cancelled"})
        if self.request_id:
            self.request_id.write({"state": "cancelled"})

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
        self.write({"state": "rejected"})
        if self.request_id:
            self.request_id.button_rejected()

    def action_open_return_cancel_wizard(self):
        """Open the ตีกลับ/แก้ไข wizard from PA draft — collects the mandatory
        reason before parking PA in ``pending_pr`` and resetting PR + sarabun."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับ/แก้ไข พจ.1"),
            "res_model": "purchase.request.approval.return.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_id": self.id},
        }

    def _reset_request_sarabun(self, reason):
        """Reset the PR's active sarabun.document back to editable ``draft``,
        reusing the SAME document (and its register number). Archives the
        completed routing chain and re-seeds a fresh one via ``_restart_chain``
        so the sender can send it again.

        Runs sudo because ``_restart_chain`` writes ``active=False`` on all
        steps including the originator — which the originator write-guard
        (``sarabun_routing_step.write``) blocks for non-sudo writes; the guard
        docstring itself flags archive as a SYSTEM operation. Authorization is
        enforced by the caller (PA-manager-gated ตีกลับ button).
        """
        self.ensure_one()
        pr = self.request_id
        if not pr:
            return
        doc = pr.active_sarabun_document_id
        if not doc:
            return
        doc = doc.sudo()
        doc.routing_step_ids._clear_activities()
        doc._restart_chain()
        doc.write({"state": "draft"})
        doc.message_post(
            body=_(
                "หนังสือถูกรีเซ็ตกลับเป็น draft เนื่องจาก พจ.1 %(pa)s ถูกส่งกลับให้แก้ไข. "
                "เหตุผล: %(reason)s"
            ) % {"pa": self.name, "reason": reason},
            subtype_xmlid="mail.mt_note",
        )

    def _action_return_for_revision(self, reason):
        """ตีกลับ/แก้ไข — send PA back to พ.1 for revision, keeping the พจ.1
        number for reuse.

        - PA → ``pending_pr`` (name preserved; ``_transition_after_sarabun_approve``
          flips it back to ``draft`` when the fresh sarabun re-completes).
        - PR → ``to_submit`` (budget commitment stays intact).
        - PR's active sarabun is reset to ``draft`` (same document + number)
          so the sender re-sends it via the existing draft, not by creating a
          new หนังสือ.
        - Redirect the user to the PR form so they can act immediately.
        """
        self.ensure_one()
        pa_body = _(
            "ตีกลับ พจ.1 %(pa)s (เก็บเลข) เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.message_post(body=pa_body, subtype_xmlid="mail.mt_note")
        pr_body = _(
            "พจ.1 %(pa)s ถูกส่งกลับให้แก้ไข. เหตุผล: %(reason)s"
        ) % {"pa": self.name, "reason": reason}
        self.request_id.message_post(body=pr_body, subtype_xmlid="mail.mt_note")
        self._reset_request_sarabun(reason)
        self.request_id.write({"state": "to_submit"})
        self.write({"state": "pending_pr"})
        return self._redirect_to_request()

    def _redirect_to_request(self):
        """Return an action that opens this PA's linked PR (พ.1) so the user
        lands on the record they need to edit after a return."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "res_id": self.request_id.id,
            "view_mode": "form",
            "target": "current",
        }

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

    def _get_sarabun_subject(self):
        return self.title or self.name

    def _sarabun_submit_guard(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("กรุณาระบุผู้ขาย (Vendor) ก่อนส่งเข้าสารบรรณ"))
        return super()._sarabun_submit_guard()

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
        reason = _("ปฏิเสธผ่านสารบรรณ: %s") % (step.note or document.name)
        self._action_do_reject(reason)
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        self.write({"state": "sarabun_returned"})
        return super()._on_sarabun_returned(document, step)

    def action_resend_to_sarabun(self):
        self.ensure_one()
        document = self.active_sarabun_document_id
        if not document:
            raise UserError(_("No active Sarabun document to resend."))
        return document.action_send()

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง Sarabun (terminal) → same effect as manual cancel wizard:
        # cascade cancel to PA + PR, and release the PR's budget commitment.
        reason = _("ยกเลิกการส่งหนังสือ %s") % document.name
        self._action_do_cancel(reason)
        pr = self.request_id
        if pr and pr.budget_commitment_id:
            try:
                pr._cancel_budget_commitment()
                pr.message_post(
                    body=_("Budget commitment %s has been cancelled")
                    % pr.budget_commitment_id.name
                )
            except UserError as e:
                pr.message_post(
                    body=_("Warning: Could not cancel budget commitment: %s")
                    % str(e)
                )
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        return self.env.ref(
            "purchase_request_approval.action_report_purchase_request_approvals"
        )
