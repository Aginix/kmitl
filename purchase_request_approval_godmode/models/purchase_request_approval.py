# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    # Shadow PA-own header fields so they are stored on the PA (per ADR-0004,
    # PA carries its own copied divergeable data) and are chatter-tracked so
    # the sarabun-sync branch's write() override can detect god-mode edits.
    # The base module accidentally re-declares these as related=; re-shadowing
    # here restores the ADR-0004 intent.
    title = fields.Char(string="Title", tracking=True)
    description = fields.Text(string="Description", tracking=True)
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        tracking=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        tracking=True,
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        domain="[('type_tax_use', 'in', ['purchase']), ('company_id', '=', company_id)]",
        check_company=True,
        context={"active_test": False},
        tracking=True,
    )

    user_has_godmode = fields.Boolean(
        compute="_compute_user_has_godmode",
        help="Whether the current user holds the PA God Mode group.",
    )

    def _compute_user_has_godmode(self):
        has = self.env.user.has_group(GODMODE_GROUP)
        for rec in self:
            rec.user_has_godmode = has

    @api.constrains(
        "amount_total",
        "line_ids",
        "line_ids.product_qty",
        "line_ids.price_unit",
    )
    def _check_godmode_amount_within_commitment(self):
        if not self.env.user.has_group(GODMODE_GROUP):
            return
        for rec in self:
            if rec.state != "approved":
                continue
            commitment = rec.budget_commitment_id
            if not commitment:
                continue
            siblings = self.search(
                [
                    ("state", "=", "approved"),
                    ("request_id.budget_commitment_id", "=", commitment.id),
                ]
            )
            total_pa = sum(siblings.mapped("amount_total"))
            rounding = (commitment.currency_id or rec.currency_id).rounding
            if float_compare(total_pa, commitment.amount, precision_rounding=rounding) > 0:
                raise ValidationError(
                    _(
                        "แก้ไข พจ.1 ในสถานะอนุมัติแล้วเกินวงเงินที่จองไว้: "
                        "ยอดรวมของ พจ.1 ทั้งหมดใน commitment %(cmt)s "
                        "= %(total).2f บาท เกินวงเงินอนุมัติ %(cap).2f บาท"
                    )
                    % {
                        "cmt": commitment.display_name,
                        "total": total_pa,
                        "cap": commitment.amount,
                    }
                )
