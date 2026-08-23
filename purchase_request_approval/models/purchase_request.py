# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    state = fields.Selection(
        selection_add=[("in_approval", "In Approval"), ("approved",)],
        ondelete={"in_approval": "set default"},
    )

    need_make_purchase_order = fields.Boolean(
        compute="_compute_need_make_purchase_order"
    )
    request_approval_count = fields.Integer(compute="_compute_request_approval_count")
    request_approval_ids = fields.One2many(
        "purchase.request.approval", inverse_name="request_id"
    )
    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")
    can_resume_returned_sarabun = fields.Boolean(
        compute="_compute_can_resume_returned_sarabun",
        help="True when this PR has a PA parked in pending_pr and a cancelled "
        "sarabun ready to be revived — drives the 'ส่งเรื่องสารบรรณ' button "
        "visibility for the two-step ตีกลับ/แก้ไข resume flow.",
    )

    @api.depends(
        "state",
        "request_approval_ids.state",
        "sarabun_document_ids.state",
    )
    def _compute_can_resume_returned_sarabun(self):
        for rec in self:
            rec.can_resume_returned_sarabun = (
                rec.state == "to_submit"
                and any(
                    pa.state == "pending_pr" for pa in rec.request_approval_ids
                )
                and any(
                    doc.state == "cancelled" for doc in rec.sarabun_document_ids
                )
            )

    def action_submit_to_sarabun(self):
        """Override the Create Sarabun entry point: when this PR came from a
        ตีกลับ/แก้ไข flow (PA in pending_pr + cancelled sarabun on file),
        revive the cancelled หนังสือ back to draft (reusing the same document
        and register number) instead of spawning a new one. Otherwise fall
        through to the standard mixin behaviour that creates a fresh sarabun."""
        self.ensure_one()
        if self.can_resume_returned_sarabun:
            return self._resume_returned_sarabun()
        return super().action_submit_to_sarabun()

    def _resume_returned_sarabun(self):
        """Revive the latest cancelled sarabun on this PR back to editable
        ``draft`` (same document + register number) and re-sync the
        origin-driven fields (``subject`` / ``sender_department_id``) from the
        current PR — so if the user edited PR.title while it was returned to
        draft, the หนังสือ picks up the new subject on resume. Called from
        :meth:`action_submit_to_sarabun` when the two-step ตีกลับ/แก้ไข resume
        conditions are met."""
        self.ensure_one()
        doc = self.env["sarabun.document"].search(
            [
                ("origin_model", "=", self._name),
                ("origin_res_id", "=", self.id),
                ("state", "=", "cancelled"),
            ],
            order="id desc",
            limit=1,
        )
        if not doc:
            raise UserError(_("ไม่พบหนังสือที่ถูกยกเลิกไว้"))
        doc = doc.sudo()
        doc.routing_step_ids._clear_activities()
        doc._restart_chain()
        resume_vals = {"state": "draft", "subject": self._get_sarabun_subject()}
        dept = self._get_sarabun_sender_department()
        if dept:
            resume_vals["sender_department_id"] = dept.id
        doc.write(resume_vals)
        doc.message_post(
            body=_(
                "หนังสือถูกนำกลับมาใช้ใหม่จากใบเดิมที่ถูกยกเลิก และ sync "
                "ค่าจาก พ.1 (subject, sender department)"
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }

    def _transition_after_sarabun_approve(self):
        for rec in self:
            if not rec.is_egp:
                rec._apply_sarabun_approve_metadata()
                rec.write({"state": "in_approval"})
                # keep-number return parks the PA in ``pending_pr`` — reuse it
                # (same พจ.1 number) instead of raising "already been created",
                # and flip it back to draft now that the new PR sarabun has
                # been approved. Re-sync copied fields from the (edited) PR
                # so the PA reflects the revised data, not the stale snapshot
                # taken at initial creation.
                existing = self.env["purchase.request.approval"].search(
                    [("request_id", "=", rec.id), ("state", "!=", "cancelled")],
                    limit=1,
                )
                if existing:
                    if existing.state == "pending_pr":
                        vals = rec._prepare_approval_sync_vals()
                        vals["state"] = "draft"
                        existing.write(vals)
                else:
                    rec.button_create_approval()
            else:
                super(PurchaseRequest, rec)._transition_after_sarabun_approve()

    def _prepare_approval_vals(self):
        return {
            "request_id": self.id,
            "requesting_department_id": self.department_id.id,
            "origin": self.name,
            "date_start": fields.Datetime.now(),
            "verified_by": False,
            "approved_by": False,
            "date_verified": False,
            "date_approved": False,
            "assigned_to": False,
            "state": "draft",
            "validation_status": "no",
            "title": self.title,
            "description": self.description,
            "procurement_type_id": self.procurement_type_id.id,
            "procurement_method_id": self.procurement_method_id.id,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "payment_type": self.payment_type,
            "partner_id": self.partner_id.id,
            "vat_included": self.vat_included,
            "tax_id": self.tax_id.id,
            "line_ids": [
                (0, 0, {
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "product_qty": line.product_qty,
                    "product_uom_id": line.product_uom_id.id,
                    "uom_text": line.uom_text,
                    "price_unit": line.price_unit,
                })
                for line in self.line_ids
            ],
        }

    def _prepare_approval_sync_vals(self):
        """Vals to re-sync an EXISTING PA record from this PR — used when a
        ตีกลับ/แก้ไข PA (parked in ``pending_pr``) is revived after the PR was
        edited. Copies the same field set as ``_prepare_approval_vals`` but
        omits identity/immutable fields (``request_id``, ``date_start``,
        ``origin``, ``state``, ``validation_status``) and resets the PA's own
        lines to mirror the PR lines (clear then create)."""
        vals = self._prepare_approval_vals()
        for key in ("request_id", "date_start", "origin", "state", "validation_status"):
            vals.pop(key, None)
        vals["line_ids"] = [(5, 0, 0)] + vals.get("line_ids", [])
        return vals

    def button_create_approval(self):
        self.ensure_one()

        exists = self.env["purchase.request.approval"].search(
            [("request_id", "=", self.id), ("state", "!=", "cancelled")], limit=1
        )

        if exists:
            raise UserError(_("Purchase Request Approval has already been created"))

        approval = self.env["purchase.request.approval"].create(
            self._prepare_approval_vals()
        )

        self.activity_feedback(
            ["purchase_request_approval.mail_activity_awaiting_approval_creation"]
        )

        link_back_message = approval._message_link_back_to_request()
        approval.message_post(body=link_back_message, message_type="comment")

        message = self._purchase_request_approval_create_message_content(approval)
        self.message_post(body=message, message_type="comment")

        return {
            "name": _("Purchase Request Approval"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "purchase.request.approval",
            "res_id": approval.id,
        }

    def button_approved(self):
        res = super().button_approved()
        self._activity_awaiting_approval_creation()

        return res

    def _activity_awaiting_approval_creation(self):
        if self.request_approval_count < 1 and self.estimated_cost <= 100000:
            self.activity_schedule(
                "purchase_request_approval.mail_activity_awaiting_approval_creation",
                user_id=self.user_id.id,
            )

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

    def _purchase_request_approval_cancelled_message_content(self, approval):
        title = _(
            "Purchase approval %(pa_name)s for your Request %(pr_name)s has been cancelled."
        ) % {
            "pr_name": self.name,
            "pa_name": approval.name,
        }
        message = '<span class="text-danger">%s</span>' % title
        return message

    def _purchase_request_approval_rejected_message_content(self, approval):
        title = _(
            "Purchase approval %(pa_name)s for your Request %(pr_name)s has been rejected."
        ) % {
            "pr_name": self.name,
            "pa_name": approval.name,
        }
        message = '<span class="text-danger">%s</span>' % title
        return message

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

    @api.depends('state')
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = True
            if (
                rec.state in ('approved', 'in_progress')
                and rec.purchase_count == 0
            ):
                rec.hide_create_po_button = False
            if rec.estimated_cost <= 100000:
                rec.hide_create_po_button = True

    def approval_make_purchase_order(self):
        self.ensure_one()
        self._create_purchase_order_from_approval()
        self._done_activity_feedback_create_purchase_order_from_approval()
        self.write({"state": "done"})
        return self.action_view_purchase_order()

    def _done_activity_feedback_create_purchase_order_from_approval(self):
        activity = "purchase_request_activity_kmitl.mail_activity_create_purchase_order"
        self.activity_feedback([activity])

    def _create_purchase_order_from_approval(self):
        self.ensure_one()
        approval = self.request_approval_ids.filtered(
            lambda a: a.state == "approved"
        )[:1]
        wizard = (
            self.env["purchase.request.line.make.purchase.order"]
            .with_context(
                active_model="purchase.request",
                active_ids=self.ids,
                active_id=self.id,
                approval_id=approval.id,
            )
            .create({
                "supplier_id": approval.partner_id.id,
                "vat_included": approval.vat_included,
                "tax_id": approval.tax_id.id,
            })
        )
        wizard.make_purchase_order()
        return wizard

    @api.depends(
        "state",
        "estimated_cost",
        "purchase_count",
        "request_approval_ids",
        "request_approval_ids.state",
        "is_egp",
    )
    def _compute_need_make_purchase_order(self):
        for rec in self:
            if (
                rec.state == "in_progress"
                and not rec.is_egp
                and rec.purchase_count == 0
                and rec.request_approval_ids
                and rec.request_approval_ids.state in ("approved")
            ):
                rec.need_make_purchase_order = True
            else:
                rec.need_make_purchase_order = False
