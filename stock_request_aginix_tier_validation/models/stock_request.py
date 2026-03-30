# -*- coding: utf-8 -*-
import logging
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = ["stock.request", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_stock_request = fields.Boolean(compute="_compute_is_stock_request")
    show_request = fields.Boolean(
        compute='_compute_show_buttons'
    )
    show_restart = fields.Boolean(
        compute='_compute_show_buttons'
    )
    can_request = fields.Boolean(compute="_compute_can_request")

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("route_id")
        return res

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.action_approved()
        
    def _compute_is_stock_request(self):
        for rec in self:
            rec.is_stock_request = rec._name == "stock.request"
        
    def _add_tier_validation_buttons(self, node, params):
        """ "close btn"""
        if self.is_stock_request:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")
    
    @api.depends("requested_by", "user_id")
    def _compute_can_request(self):
        current_user = self.env.user
        is_admin = current_user.has_group("base.group_erp_manager")
        for rec in self:
            own_by_me = (
                rec.requested_by.id == current_user.partner_id.id or
                rec.user_id.id == current_user.id
            )
            rec.can_request = own_by_me or is_admin
    
    @api.depends('need_validation', 'validation_status', 'rejected', 'state', 'can_request')
    def _compute_show_buttons(self):
        for record in self:
            record.show_request = (
                record.need_validation or
                record.validation_status == 'pending' or
                record.rejected or
                record.state != 'submitted' or
                not record.can_request
            )
            record.show_restart = (
                not record.need_validation or
                record.validation_status != 'pending' or
                not record.can_request
            )