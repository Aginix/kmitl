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
    evaluation_result_ids = fields.One2many(
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )
    requested_delivery_date = fields.Date(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def _check_state_conditions(self, vals):
        if self.env.context.get('skip_committee_wizard'):
            return False
        return super()._check_state_conditions(vals)

    def _check_allow_write_under_validation(self, vals):
        res = super()._check_allow_write_under_validation(vals)
        return res

    def _rejected_tier(self, tiers=False):
        """
        Override: แทนที่จะ set status = rejected
        ให้ set status = approved เพื่อให้ WA ไม่ถูก rejected
        แต่ยัง trigger rejected_server_action เพื่อ set committee status = other
        """
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
        # Trigger rejected_server_action manually
        # เพื่อให้ committee status = other + บันทึก comment
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
            and (not self.is_external or self.has_attachment)
        ):
            self.with_context(skip_committee_wizard=True).button_accept()
    
    def _validate_tier(self, reviews):
        """Override เพื่อเช็ค completeness หลัง validate tier"""
        res = super()._validate_tier(reviews)
        if (
            self.state == 'in_review'
            and self.completeness == 100
            and not self.env.context.get('skip_committee_wizard')
            and (not self.is_external or self.has_attachment)
        ):
            self.with_context(skip_committee_wizard=True).button_accept()
        return res

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if (
                rec.state == 'in_review'
                and rec.completeness == 100
                and not self.env.context.get('skip_committee_wizard')
                and (not rec.is_external or rec.has_attachment)
            ):
                rec.with_context(skip_committee_wizard=True).button_accept()
        return res

    def button_accept(self, force=False):
        if self.env.context.get('skip_committee_wizard'):

            for rec in self:
                if rec.is_external and not rec.has_attachment:
                    raise UserError(
                        _("Please attach at least one supporting document file before clicking accept.")
                    )

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
        res.extend(["evaluation_result_ids", "work_acceptance_committee_ids", 'state', 'date_accept'])
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
