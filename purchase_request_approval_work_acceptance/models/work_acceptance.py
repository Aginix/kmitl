# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    approval_id = fields.Many2one('purchase.request.approval', string='Purchase Request Approval', ondelete="set null", index=True)
    approval_count = fields.Integer(string='Approval Count', compute='_compute_approval_count')

    def _compute_approval_count(self):
        for wa in self:
            wa.approval_count = 1 if wa.approval_id else 0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        approval_id = self.env.context.get('default_approval_id')
        if not approval_id:
            return res
        approval = self.env['purchase.request.approval'].browse(approval_id)
        if not approval.exists():
            return res
        res.update({
            'partner_id': approval.partner_id.id,
            'company_id': approval.company_id.id,
            'currency_id': approval.currency_id.id,
            'date_due': approval.approval_date,
            'wa_tier_validation': True,
        })
        wa_lines = []
        for pa_line, pr_line in zip(
            approval.line_ids, approval.request_id.line_ids
        ):
            if not pa_line.product_qty:
                continue
            wa_lines.append(Command.create({
                'approval_line_id': pr_line.id,
                'name': pa_line.name,
                'product_uom': pa_line.product_uom_id.id,
                'uom_text': pa_line.uom_text,
                'product_id': pa_line.product_id.id,
                'price_unit': pa_line.price_unit,
                'product_qty': pa_line.product_qty,
            }))
        res['wa_line_ids'] = wa_lines
        committees = approval.mapped("work_acceptance_committee_ids")
        res['work_acceptance_committee_ids'] = [
            (0, 0, {
                "employee_id": c.employee_id.id,
                "name": c.name,
                "approve_role": c.approve_role,
                "note": c.note,
            })
            for c in committees
        ]
        return res

    def action_view_approval(self):
        self.ensure_one()
        if not self.approval_id:
            raise UserError(_("No Purchase Request Approval linked to this Work Acceptance."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request Approval'),
            'res_model': 'purchase.request.approval',
            'view_mode': 'form',
            'res_id': self.approval_id.id,
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if 'approval_id' in vals:
                approval = self.env['purchase.request.approval'].browse(vals['approval_id'])
                approval.write({'wa_ids': [(4, record.id)]})
        return records
