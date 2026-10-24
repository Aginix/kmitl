# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ReceiptKmitl(models.Model):
    _inherit = "kmitl.receipt"

    purchase_guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        string="Purchase Guarantee",
        ondelete="set null",
        index=True,
        readonly=True,
        copy=False,
    )
    receipt_kind = fields.Selection(
        selection_add=[("guarantee", "Guarantee")],
        ondelete={"guarantee": "set default"},
    )

    @api.constrains("receipt_kind", "purchase_guarantee_id")
    def _check_guarantee_receipt_has_guarantee(self):
        """A guarantee receipt without its guarantee is an orphan.

        ``receipt_kind`` is readonly in the form, so this only guards imports
        and API writes — but an orphan would print the guarantee letterhead
        with nothing backing it, and would never reach ``amount_received``.
        """
        for rec in self:
            if rec.receipt_kind == "guarantee" and not rec.purchase_guarantee_id:
                raise ValidationError(
                    _("A guarantee receipt must be linked to a purchase guarantee.")
                )

    def _receipt_sequence_vals(self, fy_be):
        """A guarantee receipt keeps its own register — see ADR-0005."""
        if self.receipt_kind == "guarantee":
            return {
                "code": "kmitl.receipt.guarantee.%s" % fy_be,
                "name": "Guarantee Receipt FY%s" % fy_be,
                "prefix": "RG/%s/" % fy_be,
            }
        return super()._receipt_sequence_vals(fy_be)

    def _report_title(self):
        if self.receipt_kind == "guarantee":
            # Not translated: both lines print side by side on every copy.
            return "ใบเสร็จรับเงินหลักประกัน", "GUARANTEE RECEIPT"
        return super()._report_title()

    def action_cancel(self):
        """Tell the guarantee its receipt is gone.

        The guarantee stays locked: cancelling a receipt is rare and someone
        has to decide whether the guarantee itself is still right, so the note
        asks rather than silently reopening it for editing.
        """
        res = super().action_cancel()
        for rec in self.filtered("purchase_guarantee_id"):
            rec.purchase_guarantee_id.sudo().message_post(
                body=_(
                    "Guarantee receipt %s was cancelled. The guarantee is still "
                    "locked — reset it to draft if it needs correcting."
                )
                % rec.name,
            )
        return res
