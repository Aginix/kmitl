# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _name = "work.acceptance"
    _inherit = ["work.acceptance", "thai.date.mixin"]
    _tier_validation_manual_config = True  # We need more buttons

    wa_tier_validation = fields.Boolean(
        string="Paperless WA",
        readonly=True,
        default=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="If checked, WA created will be approved by committee by tier valiation."
        "Each committee will be notified (by email or inbox) to approve WA.\n"
        "If not checked, WA will be approved by paper outside Odoo, "
        "and the result of WA will be filled in by procurement officer",
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

    # Late Fines
    late_days = fields.Integer(
        readonly=True,
        states={"draft": [("readonly", False)]},
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

    fines_total = fields.Monetary(
        string="Total",
        compute="_compute_fines_total",
        store=True,
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

    # Late Fines
    @api.onchange("late_days")
    def _onchange_late_days_negative(self):
        if self.late_days < 0:
            self.late_days = 0

    @api.onchange("date_receive", "date_due")
    def _onchange_late_days(self):
        late_days = 0
        if self.date_receive and self.date_due:
            late_days = (self.date_receive - self.date_due).days
        self.late_days = late_days > 0 and late_days or 0

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

    def _can_auto_accept(self):
        return True

    def _check_state_conditions(self, vals):
        if self.env.context.get('skip_committee_wizard'):
            return False
        return super()._check_state_conditions(vals)

    def _check_allow_write_under_validation(self, vals):
        res = super()._check_allow_write_under_validation(vals)
        return res

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

        return super().button_accept(force=force)
    
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
