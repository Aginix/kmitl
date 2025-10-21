# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_required_approval = fields.Boolean(
        compute="_compute_is_required_approval", store=True,
    )
    report_id = fields.Many2one(
        'purchase.request.report', string='Request Report', ondelete='set null', index=True
    )

    @api.model
    def _get_after_validation_exceptions(self):
        # จำเป็นต้องมี tier
        res = super()._get_after_validation_exceptions()
        res.append("report_id")
        return res

    @api.depends("estimated_cost")
    def _compute_is_required_approval(self):
        for rec in self:
            rec.is_required_approval = rec.estimated_cost <= 100000

    def action_open_request_report(self):
        if not self:
            raise UserError(_("No requests selected."))

        approved_requests = self.filtered(lambda r: r.state == 'approved')
        if not approved_requests:
            raise UserError(_("No approved requests selected."))

        main_payment_type = approved_requests[0].payment_type

        valid_requests = approved_requests.filtered(lambda r: r.payment_type == main_payment_type)
        if not valid_requests:
            raise UserError(_("No requests with the same payment type as the first one."))

        seq_name = self.env['ir.sequence'].next_by_code('purchase.order.approval') or _('New Report')

        # สร้าง report เดียว
        report = self.env['purchase.request.report'].sudo().create({
            'name': seq_name,
            'payment_type': main_payment_type,
            'operating_unit_id': valid_requests[0].operating_unit_id.id,
            'request_ids': [(6, 0, valid_requests.ids)],
        })

        valid_requests.sudo().write({'report_id': report.id})

        skipped = self - valid_requests
        if skipped:
            msg = _(
                "%d requests were skipped because they are not approved or have a different payment type."
            ) % len(skipped)
            report.message_post(body=msg)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request Report'),
            'res_model': 'purchase.request.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'new',
        }
