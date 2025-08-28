# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "analytic.distribution.mixin"]

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        related="request_id.budget_commitment_id",
        string="รหัสใบจองงบประมาณ",
        readonly=True,
        store=True,
        copy=False,
        help="Related budget commitment for this purchase request approval",
    )
    budget_account_id = fields.Many2one(
        "budget.account",
        string="รหัสงบประมาณ",
        related="request_id.budget_account_id",
        readonly=True,
        store=True,
        copy=False,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        related="request_id.activity_analytic_id",
        readonly=True,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        related="request_id.department_analytic_id",
        readonly=True,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        related="request_id.fund_analytic_id",
        readonly=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        related="request_id.source_analytic_id",
        readonly=True,
    )
