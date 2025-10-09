# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_required_approval = fields.Boolean(
        compute="_compute_is_required_approval", store=False, readonly=True
    )

    purchase_approval_count = fields.Integer(
        string="PR2s count", compute="_compute_purchase_approval_count", readonly=True
    )
    report_id = fields.Many2one(
        'purchase.request.report', string='Request Report', ondelete='set null', index=True
    )

    @api.depends("estimated_cost")
    def _compute_is_required_approval(self):
        for rec in self:
            rec.is_required_approval = rec.estimated_cost <= 100000

    def action_view_purchase_approval(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_approval.action_purchase_approval")
        lines = self.mapped("line_ids.purchase_lines.order_id")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase_approval.view_purchase_approval_form").id, "form")
            ]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_purchase_approval_count(self):
        for rec in self:
            rec.purchase_approval_count = len(rec.mapped("line_ids.purchase_lines.order_id").filtered("request_id"))

    # def action_open_request_report(self):
    #     self.ensure_one()
    #     report = self.env['purchase.request.report'].create({
    #             'name': f'Report for {self.name}',
    #             'company_id': self.company_id.id,
    #             'currency_id': self.currency_id.id if hasattr(self, 'currency_id') else self.env.company.currency_id.id,
    #             'request_ids': [(4, self.id)],
    #         })
    #     self.report_id = report.id
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Purchase Request Report'),
    #         'res_model': 'purchase.request.report',
    #         'res_id': report.id,
    #         'view_mode': 'form',
    #         'target': 'new',
    #     }

    def action_open_request_report(self):
        """Create one Purchase Request Report from selected requests"""
        if not self:
            raise UserError(_("No requests selected."))

        # สร้างชื่อรวม
        if len(self) == 1:
            name = f"Report for {self.name}"
        else:
            name = f"Combined Report ({len(self)} requests)"

        # ตรวจสอบ company และ currency ให้เหมือนกัน (optional)
        companies = self.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_("Please select requests from the same company."))

        currencies = self.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_("Please select requests with the same currency."))

        # สร้าง report เดียว
        report = self.env['purchase.request.report'].create({
            'name': name,
            'company_id': companies.id if companies else self.env.company.id,
            'currency_id': currencies.id if currencies else self.env.company.currency_id.id,
            'request_ids': [(6, 0, self.ids)],
        })

        # link กลับแต่ละ request
        self.write({'report_id': report.id})

        # เปิดฟอร์ม report ที่สร้าง
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request Report'),
            'res_model': 'purchase.request.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'new',
        }
