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

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequest, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    @api.depends('review_ids', 'review_ids.status', 'review_ids.reviewer_id', 'state')
    def _compute_validation_info(self):
        """คำนวณข้อมูล validation อัตโนมัติ"""
        for record in self:
            # หา review ที่ approved แล้ว เรียงตามวันที่
            approved_reviews = record.review_ids.filtered(
                lambda r: r.status == 'approved'
            ).sorted('write_date')
            
            if approved_reviews:
                # คนแรกที่ approve = verified_by
                first_approved = approved_reviews[0]
                record.verified_by = first_approved.reviewer_id
                record.date_verified = first_approved.write_date.date()
                
                # ถ้า state เป็น approved แล้ว = approved_by
                if record.state == 'approved':
                    last_approved = approved_reviews[-1]  # คนสุดท้าย
                    record.approved_by = last_approved.reviewer_id
                    record.date_approved = last_approved.write_date.date()
                else:
                    # ยังไม่ approved สุดท้าย
                    record.approved_by = False
                    record.date_approved = False
            else:
                # ยังไม่มีใคร approve เลย
                record.verified_by = False
                record.date_verified = False
                record.approved_by = False
                record.date_approved = False