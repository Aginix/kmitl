# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"

# Header fields whose value appears in the พจ.1 PDF report. God-Mode edits
# touching any of these must trigger PDF attachment regeneration so the
# Sarabun export/print flow reflects the corrected data.
# `line_ids` is included because line qty / price / name all show in the PDF.
_PDF_VISIBLE_FIELDS = frozenset(
    {
        "partner_id",
        "procurement_type_id",
        "procurement_method_id",
        "payment_type",
        "vat_included",
        "tax_id",
        "line_ids",
    }
)

# States in which God-Mode unlocks editing.
_GODMODE_STATES = ("to_approve", "approved")


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    # Shadow header fields so God-Mode users can edit them in to_approve /
    # approved states. `title` and `description` are deliberately NOT shadowed
    # here (they are PA-own already after the base-module fix, but remain
    # locked in the God-Mode view — treated as read-only metadata copied
    # from the parent purchase.request).
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
        """God-Mode writes are silent (no chatter / no follower notification)
        and refresh the PA PDF attachment when a field visible in the report
        has changed.
        """
        if self.env.user.has_group(GODMODE_GROUP):
            silent_self = self.with_context(
                tracking_disable=True,
                mail_notrack=True,
                mail_create_nolog=True,
            )
            res = super(PurchaseRequestApproval, silent_self).write(vals)
            if set(vals) & _PDF_VISIBLE_FIELDS:
                for rec in silent_self:
                    if rec.state in _GODMODE_STATES:
                        rec._regenerate_report_pdf()
            return res
        return super().write(vals)

    def _regenerate_report_pdf(self):
        """Drop the currently-stored พจ.1 PDF attachment and let the base
        `report_generate()` create a fresh one. Called from `write()` after a
        God-Mode edit that touches PDF-visible fields, so the Sarabun
        export/print flow serves the corrected document instead of the
        one snapshotted at `button_to_approve()` time.
        """
        self.ensure_one()
        if not self.name:
            return
        filename = self.name + ".pdf"
        old_attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("name", "=", filename),
            ]
        )
        old_attachments.unlink()
        self.report_generate()
