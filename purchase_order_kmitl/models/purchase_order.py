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

    invoice_plan_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="purchase_id",
        states=READONLY_STATES,
    )

    use_invoice_plan = fields.Boolean(
        states=READONLY_STATES,
    )
    
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
        tracking=True,
    )

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        tracking=True,
        states=READONLY_STATES,
    )

    date_planned = fields.Datetime(
        string="Date End"
    )

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        states=READONLY_STATES,
        tracking=True
    )

    payment_type = fields.Selection(
        [
            ("direct", "Direct paid"),
            ("advance", "Advance"),
            ("prepaid", "Prepaid"),
        ],
        tracking=True,
        string="Payment Type",
        states=READONLY_STATES,
    )

    state = fields.Selection(selection_add=[
        ("purchase", "Open"),
        ("done", "Done")
    ])

    # --- Contract Guarantee Report fields ---
    guarantee_ids = fields.One2many("purchase.guarantee", "purchase_id")

    contract_guarantee_type_id = fields.Many2one(
        "purchase.guarantee.type",
        string="ประเภทหลักประกัน",
        compute="_compute_contract_guarantee_info",
        store=True,
    )
    contract_guarantee_amount = fields.Monetary(
        string="มูลค่าหลักประกัน",
        compute="_compute_contract_guarantee_info",
        store=True,
    )
    contract_guarantee_date_due_display = fields.Char(
        string="วันที่สิ้นสุดอายุหลักประกัน",
        compute="_compute_contract_guarantee_info",
        store=True,
    )
    contract_guarantee_return_state = fields.Selection(
        selection=[("returned", "คืนแล้ว"), ("pending", "ยังไม่ได้คืน")],
        string="สถานะหลักประกัน",
        compute="_compute_contract_guarantee_info",
        store=True,
    )

    @api.depends(
        "guarantee_ids.guarantee_method_id",
        "guarantee_ids.guarantee_type_id",
        "guarantee_ids.amount",
        "guarantee_ids.date_due_guarantee",
        "guarantee_ids.date_return",
    )
    def _compute_contract_guarantee_info(self):
        for rec in self:
            guarantee = rec.guarantee_ids.filtered(
                lambda g: g.guarantee_method_id.default_for_model == "purchase.order.po"
            )[:1]
            rec.contract_guarantee_type_id = guarantee.guarantee_type_id
            rec.contract_guarantee_amount = guarantee.amount
            if guarantee:
                if guarantee.date_due_guarantee:
                    rec.contract_guarantee_date_due_display = (
                        guarantee.date_due_guarantee.strftime("%d/%m/%Y")
                    )
                else:
                    rec.contract_guarantee_date_due_display = "จนกว่าจะพ้นภาระผูกพันธ์"
                rec.contract_guarantee_return_state = (
                    "returned" if guarantee.date_return else "pending"
                )
            else:
                rec.contract_guarantee_date_due_display = False
                rec.contract_guarantee_return_state = False

    def action_view_purchase_request(self):
        self.ensure_one()
        if not self.request_id:
            return

        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': self.request_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
