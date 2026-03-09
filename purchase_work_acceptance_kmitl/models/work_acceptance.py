# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    evaluation_result_ids = fields.One2many(
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )

    requested_delivery_date = fields.Date(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    all_committee_validated = fields.Boolean(
        compute='_compute_all_committee_validated',
        store=True,
        string='All Committee Validated',
    )

    def _check_state_conditions(self, vals):
        if self.env.context.get('skip_committee_wizard'):
            return False
        return super()._check_state_conditions(vals)

    @api.depends('work_acceptance_committee_ids.status')
    def _compute_all_committee_validated(self):
        for rec in self:
            committees = rec.work_acceptance_committee_ids
            if committees and all(c.status == 'accept' for c in committees):
                rec.all_committee_validated = True
                if not rec.is_external or (rec.is_external and rec.has_attachment):
                    rec.with_context(skip_committee_wizard=True).button_accept()
            else:
                rec.all_committee_validated = False

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if (
                rec.state == 'in_review'
                and rec.validation_status == 'validated'
                and not self.env.context.get('skip_committee_wizard')
                and (not rec.is_external or (rec.is_external and rec.has_attachment))
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
    
    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.extend(['state', 'date_accept'])
        return res

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

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }
