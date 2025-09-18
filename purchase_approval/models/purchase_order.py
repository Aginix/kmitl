# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "tier.validation"]

    state = fields.Selection(
        selection_add=[
            ("draft", "Draft"),
            ("sent", "RFQ Sent"),
            ("to approve", "To Approve"),
        ]
    )
    request_date = fields.Datetime(
        string="Request On", readonly=True, copy=False, default=fields.Datetime.now
    )
    approval_ref = fields.Char(
        "PR2 Reference", copy=False, readonly=True, default="New"
    )
    approved_by = fields.Many2one(
        "res.users", string="Approved By", readonly=True, copy=False, tracking=True
    )
    approved_on = fields.Datetime(string="Approved On", readonly=True, copy=False)

    # ==== Purchase Request ====
    request_id = fields.Many2one(
        "purchase.request", string="Purchase Request", readonly=True, copy=False
    )
    request_title = fields.Char(related="request_id.title", store=True, readonly=True, copy=False)
    request_description = fields.Text(
        related="request_id.description", store=True, readonly=True, copy=False
    )
    procurement_type_id = fields.Many2one(related="request_id.procurement_type_id", store=False, readonly=True, copy=False)
    procurement_method_id = fields.Many2one(related="request_id.procurement_method_id", store=False, readonly=True, copy=False)
    payment_type = fields.Selection(related="request_id.payment_type", store=False, readonly=True, copy=False)
    contract_type = fields.Selection(related="request_id.contract_type", store=False, readonly=True, copy=False)
    requested_by = fields.Many2one(
        comodel_name="res.users",
        related="request_id.requested_by",
        string="Requested by",
        store=True,
        copy=False,
    )
    request_cost = fields.Monetary(
        related="request_id.estimated_cost",
        string="Request Cost",
        store=False,
        copy=False,
    )
    request_line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        related="request_id.line_ids",
        string="Products to Purchase",
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "request_id" in vals:
                vals["approval_ref"] = self.env["ir.sequence"].next_by_code(
                    "purchase.order.approval"
                )
        return super().create(vals_list)

    def request_validation(self):
        if self.request_id:
            self.write({'state': 'to approve'})
        return super().request_validation()

    def button_approval_to_purchase(self):
        self.write({'state': 'purchase'})

    def validate_tier(self):
        super().validate_tier()
        _logger.info({
            'need_validation': self.need_validation,
        })
        if not self.need_validation:
            self.write({'state': 'purchase'})

    def action_view_purchase_order_from_approval(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        action["views"] = [
            (self.env.ref("purchase.purchase_order_form").id, "form")
        ]
        action["res_id"] = self.id
        return action

    def _get_all_validation_exceptions(self):
        res = super()._get_all_validation_exceptions()
        fields = self.env['ir.model.fields'].search([('model', '=', 'purchase.order'), ('readonly', '=', False)]).mapped("name")
        return res + fields

    def name_get(self):
        res = super().name_get()
        name_mapping = dict(res)
        for rec in self:
            if self.env.context.get('purchase_approval') and rec.approval_ref:
                name_mapping[rec.id] = rec.approval_ref
        return list(name_mapping.items())
