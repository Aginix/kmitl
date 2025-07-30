# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_editable = fields.Boolean(compute="_compute_is_editable")

    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
        store=True,
        compute="_compute_validation_info"
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
        store=True,
        compute="_compute_validation_info"
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
        store=True,
        compute="_compute_validation_info"
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
        store=True,
        compute="_compute_validation_info"
    )

    committed_by = fields.Many2one(
        'res.users', 
        string='Committed by', 
        readonly=True)
    date_committed = fields.Datetime(
        string='Committed Date', 
        readonly=True)
    
    validate_by = fields.Many2one(
        'res.users', 
        string='Validate by', 
        readonly=True)
    date_validate = fields.Datetime(
        string='Validate Date', 
        readonly=True)


    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('commit', 'Committed'),
        ('validate', 'Validated'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, index=True, copy=False, tracking=True, default='draft')

    def action_submit(self):
        for rec in self:
            rec.state = 'submit'

    def action_commit(self):
        for rec in self:
            rec.state = 'commit'
            rec.committed_by = self.env.user
            rec.date_committed = fields.Datetime.now()

    def action_validate(self):
        for rec in self:
            rec.state = 'validate'
            rec.validate_by = self.env.user
            rec.date_validate = fields.Datetime.now()

    def button_draft(self):
        res = super().button_draft()
        for rec in self:
            rec.committed_by = False
            rec.date_committed = False
            rec.validate_by = False
            rec.date_validate = False
        return res

    is_finance_user = fields.Boolean(
        string='Is Finance User',
        compute='_compute_is_finance_user',
        store=False
    )
    
    @api.depends_context('uid')
    def _compute_is_finance_user(self):
        for record in self:
            record.is_finance_user = self.env.user.has_group(
                'kmitl_purchase_request_tier_validation.group_finance'
            )        

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequest, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    @api.depends('review_ids', 'review_ids.status', 'review_ids.reviewer_id', 'state')
    def _compute_validation_info(self):
        for record in self:
            approved_reviews = record.review_ids.filtered(
                lambda r: r.status == 'approved'
            ).sorted('write_date')
            
            if approved_reviews:
                first_approved = approved_reviews[0]
                record.verified_by = first_approved.reviewer_id
                record.date_verified = first_approved.write_date.date()
                
                if record.state == 'approved':
                    last_approved = approved_reviews[-1]
                    record.approved_by = last_approved.reviewer_id
                    record.date_approved = last_approved.write_date.date()
                else:
                    record.approved_by = False
                    record.date_approved = False
            else:
                record.verified_by = False
                record.date_verified = False
                record.approved_by = False
                record.date_approved = False

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "submit",
                "commit",
                "validate",
                "to_approve",
                "approved",
                "rejected",
                "in_progress",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True