# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    wa_ids = fields.One2many(
        comodel_name="work.acceptance",
        inverse_name="disbursement_request_id",
        string="Work Acceptances",
        readonly=True,
    )

    wa_count = fields.Integer(
        compute="_compute_wa_count",
        store=True,
    )

    fines_late = fields.Monetary(
        string="Fines Amount",
        compute="_compute_fines_late",
        tracking=True,
        store=True,
        readonly=True
    )

    fines_total = fields.Monetary(
        string="Fined Total",
        compute="_compute_fines_total",
        store=True,
    )

    @api.depends("line_ids.account_id.code", "line_ids.price_subtotal")
    def _compute_fines_late(self):
        for rec in self:
            fine_lines = rec.line_ids.filtered(
                lambda l: l.account_id.code == "4310000003"
            )
            rec.fines_late = abs(sum(fine_lines.mapped("price_subtotal")))

    @api.depends("amount_untaxed", "fines_late")
    def _compute_fines_total(self):
        for rec in self:
            result = rec.amount_untaxed - rec.fines_late
            rec.fines_total = max(result, 0)

    @api.depends("wa_ids")
    def _compute_wa_count(self):
        for rec in self:
            rec.wa_count = len(rec.wa_ids)

    def _get_return_source(self):
        """A DR backed by a Work Acceptance returns to the WA (not the PO its
        ``reference`` points at): the correctable data lives on the WA. This
        bridge depends on purchase_order_disbursement, so this override wins over
        the PO one in the MRO."""
        return self.wa_ids[:1] or super()._get_return_source()

    def action_sign(self):
        """Override: mark WA as disbursed เมื่อ submitted → unlock สร้าง WA ใหม่ได้"""
        res = super().action_sign()
        for rec in self:
            if rec.wa_ids:
                rec.wa_ids.write({"is_disbursed": True})
        return res

    def action_draft(self):
        """Override: reset WA flag เมื่อ reset to draft"""
        res = super().action_draft()
        for rec in self:
            if rec.wa_ids:
                rec.wa_ids.write({"is_disbursed": False})
        return res

    def action_view_work_acceptances(self):
        self.ensure_one()
        if not self.wa_ids:
            raise UserError(_("No Work Acceptances linked to this request."))
        if len(self.wa_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Work Acceptance"),
                "res_model": "work.acceptance",
                "view_mode": "form",
                "res_id": self.wa_ids.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Work Acceptances"),
            "res_model": "work.acceptance",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.wa_ids.ids)],
            "target": "current",
        }

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.price_tax",
        "line_ids.price_total",
        "line_ids.amount_wht",
        "line_ids.account_id.code",
    )
    def _compute_amount_all(self):
        super()._compute_amount_all()
        for request in self:
            fine_lines = request.line_ids.filtered(
                lambda l: l.account_id.code == "4310000003"
            )
            fines_amount = abs(sum(fine_lines.mapped("price_subtotal")))

            request.amount_untaxed = request.amount_untaxed + fines_amount

            fines_total = request.amount_untaxed - fines_amount
            amount_total = fines_total + request.amount_tax
            request.amount_total = amount_total
            request.amount_net = amount_total - request.amount_wht
