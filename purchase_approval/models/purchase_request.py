# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_required_approval = fields.Boolean(
        compute="_compute_is_required_approval", store=False, readonly=True
    )
    report_id = fields.Many2one(
        'purchase.request.report', string='Request Report', ondelete='set null', index=True
    )

    @api.depends("estimated_cost")
    def _compute_is_required_approval(self):
        for rec in self:
            rec.is_required_approval = rec.estimated_cost <= 100000

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

        seq_name = self.env['ir.sequence'].next_by_code('purchase.order.approval')
        # สร้าง report เดียว
        report = self.env['purchase.request.report'].create({
            'name': seq_name,
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
