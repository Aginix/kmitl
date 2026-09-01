# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"

# States in which God-Mode unlocks editing.
_GODMODE_STATES = ("to_approve", "approved")


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        domain="[('type_tax_use', 'in', ['purchase']), ('company_id', '=', company_id)]",
        check_company=True,
        context={"active_test": False},
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
            if rec.state not in _GODMODE_STATES:
                continue
            commitment = rec.budget_commitment_id
            if not commitment:
                continue
            siblings = self.search(
                [
                    ("state", "in", list(_GODMODE_STATES)),
                    ("request_id.budget_commitment_id", "=", commitment.id),
                ]
            )
            total_pa = sum(siblings.mapped("amount_total"))
            rounding = (commitment.currency_id or rec.currency_id).rounding
            if float_compare(total_pa, commitment.amount, precision_rounding=rounding) > 0:
                raise ValidationError(
                    _(
                        "แก้ไข พจ.1 เกินวงเงินที่จองไว้: "
                        "ยอดรวมของ พจ.1 ทั้งหมดใน commitment %(cmt)s "
                        "= %(total).2f บาท เกินวงเงินอนุมัติ %(cap).2f บาท"
                    )
                    % {
                        "cmt": commitment.display_name,
                        "total": total_pa,
                        "cap": commitment.amount,
                    }
                )

    def write(self, vals):
        """God-Mode writes are silent (no chatter / no follower notification)."""
        if self.env.user.has_group(GODMODE_GROUP):
            silent_self = self.with_context(
                tracking_disable=True,
                mail_notrack=True,
                mail_create_nolog=True,
            )
            return super(PurchaseRequestApproval, silent_self).write(vals)
        return super().write(vals)
