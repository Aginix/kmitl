# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Purchase_request(models.Model):
    _inherit = 'purchase.request'

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    to_create = fields.Selection(
        related="purchase_type_id.to_create",
    )
    procurement_method_ids = fields.Many2many(
        related="purchase_type_id.procurement_method_ids",
    )
    expense_reason = fields.Text(
        string="Reason",
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )

    tor_document_ids = fields.One2many(
        'purchase.request.attachment', 'request_id',
        string="ข้อกำหนดคุณลักษณะ (TOR)",
        domain=[('attachment_type', '=', 'tor')]
    )
    rfq_attachment_ids = fields.One2many(
        'purchase.request.attachment', 'request_id',
        string="ใบเสนอราคา",
        domain=[('attachment_type', '=', 'rfq')]
    )
    etc_document_ids = fields.One2many(
        'purchase.request.attachment', 'request_id',
        string="อื่นๆ",
        domain=[('attachment_type', '=', 'etc')]
    )

    title = fields.Text(string="ชื่อเรื่อง")

    source_of_fund = fields.Char(string="แหล่งเงิน")
    
    plan = fields.Char(string="แผน/งาน/กิจกรรมหลัก/กิจกรรมรอง/ย่อย")

    fund = fields.Char(string="กองทุน")

    budget_type = fields.Char(string="ประเภทงบประมาณ")

    expense_code = fields.Char(string="รหัสค่าใช้จ่าย")


    # substate_sequence = fields.Integer(related="substate_id.sequence")

    def _get_domain_purchase_type(self):
        return [("visible_on_purchase_request", "=", True)]

    # def get_estimated_cost_currency(self, date=False):
    #     """Get estimated cost with currency"""
    #     self.ensure_one()
    #     date = date or fields.Date.context_today(self)
    #     estimated_cost = sum(self.line_ids.mapped("estimated_cost"))
    #     if self.currency_id != self.company_id.currency_id:
    #         # check installing module `purchase_request_manual_currency`
    #         # it should convert following custom rate
    #         if hasattr(self, "manual_currency") and self.manual_currency:
    #             rate = (
    #                 self.custom_rate
    #                 if self.type_currency == "inverse_company_rate"
    #                 else (1.0 / self.custom_rate)
    #             )
    #             estimated_cost = estimated_cost * rate
    #         else:
    #             estimated_cost = self.currency_id._convert(
    #                 estimated_cost, self.company_id.currency_id, self.company_id, date
    #             )
    #     return estimated_cost

    # def action_to_substate(self):
    #     self.ensure_one()
    #     sequence = self.env.context.get("to_substate_sequence", 0)
    #     substate = self.env["base.substate"].search(
    #         [("model", "=", "purchase.request"), ("sequence", "=", sequence)], limit=1
    #     )
    #     self.write(
    #         {
    #             "substate_id": substate.id,
    #             "verified_by": self.env.user.id,
    #             "date_verified": fields.Date.context_today(self),
    #         }
    #     )

    @api.onchange("purchase_type_id")
    def _onchange_purchase_type_id(self):
        procurement_methods = self.purchase_type_id.procurement_method_ids
        self.update(
            {
                "procurement_method_id": len(procurement_methods) == 1
                and procurement_methods.id
                or False,
            }
        )

    # def button_approved(self):
    #     self.write(
    #         {
    #             "approved_by": self.env.user.id,
    #             "date_approved": fields.Date.context_today(self),
    #         }
    #     )
    #     return super().button_approved()

    # def _get_condition_reset_reject(self):
    #     po_manager = self.user_has_groups("purchase.group_purchase_user")
    #     substate_verify = self.env.ref(
    #         "l10n_th_gov_purchase_request.base_substate_verified"
    #     )
    #     return self.filtered(
    #         lambda l: (
    #             l.state in ["approved", "done"]
    #             or (l.state == "to_approve" and l.substate_id == substate_verify)
    #         )
    #         and not po_manager
    #         and not self._context.get("bypass_pr_reject")
    #     )

    # def button_rejected(self):
    #     """Allows the Procurement to reject documents after
    #     procurement approved by procurement only."""
    #     if self._get_condition_reset_reject():
    #         raise UserError(
    #             _(
    #                 "You are not allowed to reject a document that has already been approved.\n"
    #                 "Please contact the Procurement."
    #             )
    #         )
    #     return super().button_rejected()

    # def button_draft(self):
    #     """Allows the Procurement to reset documents after
    #     procurement approved by procurement only."""
    #     if self._get_condition_reset_reject():
    #         raise UserError(
    #             _(
    #                 "You are not allowed to reset a document that has already been approved.\n"
    #                 "Please contact the Procurement."
    #             )
    #         )
    #     return super().button_draft()