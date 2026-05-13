# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _name = "work.acceptance"
    _inherit = ["work.acceptance", "thai.date.mixin"]
    _tier_validation_manual_config = True  # We need more buttons
    _state_from = ["in_review"]
    _state_to = ["accept"]

    state = fields.Selection(
        selection_add=[("in_review", "In Review"), ("accept",)]
    )

    wa_tier_validation = fields.Boolean(
        string="Paperless WA",
        readonly=True,
        default=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="If checked, WA created will be approved by committee by tier validation."
        "Each committee will be notified (by email or inbox) to approve WA.\n"
        "If not checked, WA will be approved by paper outside Odoo, "
        "and the result of WA will be filled in by procurement officer",
    )
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        domain=[("res_model", "=", "work.acceptance")],
        tracking=True,
    )

    work_acceptance_committee_ids = fields.One2many(
        comodel_name="work.acceptance.committee",
        inverse_name="wa_id",
        string="Work Acceptance Committees",
        copy=True,
    )
    completeness = fields.Float(
        string="Progress",
        compute="_compute_completeness",
        store=True,
    )
    requested_delivery_date = fields.Date(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # convert from Datetime to Date
    date_due = fields.Date(
        string="Due Date",
        compute="_compute_date_due",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_receive = fields.Date(
        string="Received Date",
        default=lambda self: self._default_start_date(),
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_receive = fields.Date(
        string="Received Date",
        default=lambda self: self._default_start_date(),
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # PO date snapshots (captured at WA creation, immune to PO edits)
    po_date_order_date = fields.Date(
        string="PO Contract Date",
        copy=False,
    )
    po_work_start = fields.Date(
        string="PO Work Start",
        copy=False,
    )
    current_work_end = fields.Date(
        compute="_compute_current_work_end",
    )
    po_work_end_original = fields.Date(
        string="PO Work End Original",
        related='purchase_id.work_end_original',
    )

    # Late Fines
    late_days = fields.Integer(
        compute="_compute_late_days",
        store=True,
        readonly=False,
        tracking=True,
        help="Late day(s) from Received Date - Due Date",
    )

    fines_rate = fields.Monetary(
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="Default fines per day. Can be overwritten",
    )

    fines_late = fields.Monetary(
        string="Fines Amount",
        tracking=True,
        compute="_compute_fines_late",
        store=True
    )

    price_subtotal = fields.Monetary(
        compute="_compute_price_subtotal",
        string="Project value",
        store=True,
    )
    amount_tax = fields.Monetary(
        compute="_compute_amount_tax",
        string="Tax Amount",
        store=True,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        string="Total Amount",
        store=True,
    )

    fines_total = fields.Monetary(
        string="Total",
        compute="_compute_fines_total",
        store=True,
    )

    # Construction contract dates
    is_construction_contract = fields.Boolean(
        compute="_compute_is_construction_contract",
    )
    is_delivery_late = fields.Boolean(
        compute="_compute_is_delivery_late",
        store=True,
    )
    date_committee_received = fields.Date(
        string="วันที่คณะกรรมการได้รับเอกสาร",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_contract_complete = fields.Date(
        string="วันที่เสร็จถูกต้องตามสัญญา",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_work_handover = fields.Date(
        string="วันที่รับมอบงานแล้ว",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    _sql_constraints = [
        ("late_days", "CHECK (late_days>=0)", "Wrong Late Days, it must be positive!"),
        (
            "fines_rate",
            "CHECK (fines_rate>=0)",
            "Wrong Fines Rate, it must be positive!",
        ),
        (
            "fines_late",
            "CHECK (fines_late>=0)",
            "Wrong Fines Amount, it must be positive!",
        ),
    ]

    def _default_start_date(self):
        return fields.Date.today()

    @api.depends("requested_delivery_date", "date_due")
    def _compute_is_delivery_late(self):
        accepted = self.filtered(lambda r: r.state == 'accept')
        if accepted:
            self.env.cr.execute(
                "SELECT id, is_delivery_late FROM work_acceptance"
                " WHERE id = ANY(%s)",
                [list(accepted.ids)],
            )
            stored = dict(self.env.cr.fetchall())
            for rec in accepted:
                rec.is_delivery_late = stored.get(rec.id, False)
        for rec in (self - accepted):
            rec.is_delivery_late = bool(
                rec.requested_delivery_date
                and rec.date_due
                and rec.requested_delivery_date > rec.date_due
            )

    @api.depends("purchase_id")
    def _compute_is_construction_contract(self):
        for rec in self:
            rec.is_construction_contract = bool(
                getattr(rec.purchase_id.contract_type_id, "is_construction", False)
            )

    @api.depends("date_due")
    def _compute_current_work_end(self):
        for rec in self:
            if rec.date_due:
                rec.current_work_end = rec.date_due + timedelta(days=1)
            else:
                rec.current_work_end = False

    def _can_auto_accept(self):
        return True

    def _get_under_validation_allowed_fields(self):
        fields = super()._get_under_validation_allowed_fields()
        return fields + ["state"]

    def request_validation(self):
        self.write({"state": "in_review"})
        return super().request_validation()

    def button_review(self):
        self.write({"state": "in_review"})

    def _check_state_conditions(self, vals):
        if self.env.context.get('skip_committee_wizard'):
            return False
        return super()._check_state_conditions(vals)

    def _rejected_tier(self, tiers=False):
        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        # Set approved แทน rejected เพื่อไม่ให้ WA ถูก set rejected = True
        user_reviews.write({
            'status': 'approved',
            'done_by': self.env.user.id,
            'reviewed_date': fields.Datetime.now(),
        })
        for review in user_reviews:
            if review.definition_id.rejected_server_action_id:
                review.definition_id.rejected_server_action_id\
                    .with_context(
                        active_id=self.id,
                        active_model=self._name,
                    ).sudo().run()
        self._update_counter({'review_deleted': True})

        if (
            self.state == 'in_review'
            and self.completeness == 100
            and not self.env.context.get('skip_committee_wizard')
            and self._can_auto_accept()
        ):
            self.with_context(skip_committee_wizard=True).button_accept()

    def _validate_tier(self, reviews):
        res = super()._validate_tier(reviews)
        if (
            self.state == 'in_review'
            and self.completeness == 100
            and not self.env.context.get('skip_committee_wizard')
            and self._can_auto_accept()
        ):
            self.with_context(skip_committee_wizard=True).button_accept()
        return res

    def button_accept(self, force=False):
        for rec in self:
            if not rec.wa_tier_validation and not rec.attachment_ids:
                raise UserError(
                    _("กรุณาแนบหลักฐานการตรวจรับ")
                )

        if self.env.context.get('skip_committee_wizard'):
            self.mapped('review_ids').unlink()
            self._unlink_zero_quantity()
            date_accept = force or fields.Datetime.now()
            self.with_context(
                skip_validation_check=True
            ).write({
                'state': 'accept',
                'date_accept': date_accept,
            })
            return True

        for rec in self:
            committees = rec.work_acceptance_committee_ids
            if committees and rec.completeness < 100:
                return rec._action_open_committee_wizard()

        result = super().button_accept(force=force)
        return result

    @api.depends("work_acceptance_committee_ids.status")
    def _compute_completeness(self):
        for rec in self:
            committees = len(rec.work_acceptance_committee_ids)
            rec.completeness = 0
            if committees:
                reviewed = len(rec.work_acceptance_committee_ids.filtered("status"))
                rec.completeness = reviewed / committees * 100

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.extend(["work_acceptance_committee_ids", 'state', 'date_accept'])
        return res

    def _clear_data_committee(self):
        """Clear data work acceptance committee"""
        self.mapped("work_acceptance_committee_ids").write(
            {
                "status": "",
                "note": "",
            }
        )

    def button_draft(self):
        self._clear_data_committee()
        return super().button_draft()

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return

        return {
            "name": _("Purchase Order"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": self.purchase_id.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
            "context": self.env.context,
        }

    # Late Fines
    @api.onchange("late_days")
    def _onchange_late_days_negative(self):
        if self.late_days < 0:
            self.late_days = 0

    @api.depends("requested_delivery_date", "date_due")
    def _compute_late_days(self):
        for rec in self:
            late_days = 0
            if rec.requested_delivery_date and rec.date_due:
                late_days = (rec.requested_delivery_date - rec.date_due).days
            rec.late_days = late_days if late_days > 0 else 0

    @api.onchange("fines_rate")
    def _onchange_fines_rate(self):
        if self.fines_rate < 0:
            self.fines_rate = 0

    @api.depends("late_days", "fines_rate")
    def _compute_fines_late(self):
        for rec in self:
            rec.fines_late = rec.late_days * rec.fines_rate

    @api.depends("price_subtotal", "fines_late")
    def _compute_fines_total(self):
        for rec in self:
            result = rec.price_subtotal - rec.fines_late
            rec.fines_total = max(result, 0)

    @api.depends("wa_line_ids", "wa_line_ids.price_subtotal")
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = sum(rec.wa_line_ids.mapped("price_subtotal"))

    @api.depends("wa_line_ids", "wa_line_ids.price_subtotal", "wa_line_ids.purchase_line_id")
    def _compute_amount_tax(self):
        for rec in self:
            amount_tax = 0.0
            for line in rec.wa_line_ids:
                taxes = line.purchase_line_id.taxes_id
                if taxes:
                    tax_result = taxes.compute_all(
                        line.price_unit,
                        rec.currency_id,
                        line.product_qty,
                        line.product_id,
                        rec.partner_id,
                    )
                    amount_tax += sum(t["amount"] for t in tax_result["taxes"])
            rec.amount_tax = amount_tax

    @api.depends("price_subtotal", "amount_tax")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.price_subtotal + rec.amount_tax

    def _action_open_committee_wizard(self):
        self.ensure_one()
        return {
            'name': _('Work Acceptance Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'work.acceptance.committee.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wa_id': self.id,
            },
        }


class WorkAcceptanceLine(models.Model):
    _inherit = "work.acceptance.line"

    date_due = fields.Date(related="wa_id.date_due", string="Due Date", readonly=True)
    date_receive = fields.Date(
        related="wa_id.date_receive", string="Received Date", readonly=True
    )
