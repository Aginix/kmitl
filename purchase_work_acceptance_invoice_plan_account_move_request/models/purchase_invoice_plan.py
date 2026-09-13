# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseInvoicePlan(models.Model):
    _inherit = 'purchase.invoice.plan'

    move_request_id = fields.Many2one(
        comodel_name="account.move.request",
        string="Move Request",
        ondelete="set null",
    )

    def _prepare_move_request_line_vals(self, wa_line):
        account = (
            wa_line.product_id.property_account_expense_id
            or wa_line.product_id.categ_id.property_account_expense_categ_id
        )
        return {
            "product_id": wa_line.product_id.id,
            "name": wa_line.name,
            "quantity": wa_line.product_qty,
            "price_unit": wa_line.price_unit,
            "account_id": account.id if account else False,
            "tax_ids": [Command.set(self.purchase_id.order_line[0].taxes_id.ids)],
            "analytic_distribution": self.purchase_id.order_line[0].analytic_distribution,
        }

    def _prepare_move_request_vals(self):
        line_vals = [
            Command.create(self._prepare_move_request_line_vals(wa_line))
            for wa_line in self.wa_id.wa_line_ids
        ]

        return {
            "purchase_id": self.purchase_id.id,
            "partner_id": self.partner_id.id,
            "line_ids": line_vals,
            "ref": ", ".join(self.wa_id.wa_line_ids.mapped("name")),
            "invoice_plan_id": self.id,
        }

    def action_move_request(self):
        self.ensure_one()
        move_request = self.env["account.move.request"].create(
            self._prepare_move_request_vals()
        )
        self.move_request_id = move_request.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.request",
            "view_mode": "form",
            "res_id": move_request.id,
            "target": "current",
        }
