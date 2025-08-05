# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    contractor_name = fields.Char(
        string='ชื่อผู้ว่าจ้าง',
        compute='_compute_contractor_name',
        store=True,
        states=READONLY_STATES
    )
    contract_start_date = fields.Date(string='วันที่เริ่มสัญญา',states=READONLY_STATES)
    contract_end_date = fields.Date(string='วันที่สิ้นสุดสัญญา',states=READONLY_STATES)
    po_custom_number = fields.Char(
        string='หมายเลขคำสั่งซื้อ',
        copy=False,
        readonly=True,
        required=True,
        default='New',states=READONLY_STATES
    )
    purchase_type = fields.Selection(
        selection=[
            ('order', 'ใบสั่งซื้อ/จ้าง'),
            ('contract_buy', 'สัญญาซื้อขาย'),
            ('contract_construction', 'สัญญาจ้างก่อสร้าง'),
        ],
        string='ประเภทสัญญา/ใบสั่งซื้อ/จ้าง',
        required=True,states=READONLY_STATES
    )
    work_start_date = fields.Date(string='วันที่เริ่มงาน',states=READONLY_STATES)
    work_end_date = fields.Date(string='วันที่สิ้นสุดงาน',states=READONLY_STATES)
    purchase_title = fields.Char(string='ชื่อใบสั่งซื้อ/จ้าง', required=True,states=READONLY_STATES)
    penalty_per_day = fields.Float(string='ค่าปรับต่อวัน',states=READONLY_STATES)
    pr1_id = fields.Many2one('purchase.request', string='Ref PR1',states=READONLY_STATES)
    pr2_id = fields.Many2one('purchase.request.form', string='Ref PR2',states=READONLY_STATES)

    @api.depends('company_id')
    def _compute_contractor_name(self):
        for order in self:
            order.contractor_name = order.company_id.name if order.company_id else ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order')
        return super().create(vals_list)
