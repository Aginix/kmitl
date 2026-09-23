from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="purchase_guarantee_id",
        string="Payments",
    )
    payment_count = fields.Integer(
        compute="_compute_payment_count",
    )
    has_active_payment = fields.Boolean(
        compute="_compute_has_active_payment",
    )

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends("payment_ids.state")
    def _compute_has_active_payment(self):
        for rec in self:
            rec.has_active_payment = any(
                p.state != "cancel" for p in rec.payment_ids
            )

    def action_view_payments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments"
        )
        if self.payment_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.payment_ids.id
        else:
            action["domain"] = [("id", "in", self.payment_ids.ids)]
        return action

    def _prepare_account_payment_vals(self):
        if self.guarantee_method_id == self.env.ref("l10n_th_gov_purchase_guarantee.bid_guarantee"):
            payment_type = self.env.ref(
                "finance_kmitl.payment_type_bid_guarantee_receive")
        elif self.guarantee_method_id == self.env.ref("l10n_th_gov_purchase_guarantee.advance_payment_guarantee"):
            payment_type = self.env.ref(
                "finance_kmitl.payment_type_guarantee_receive")
        else:
            raise UserError(
                _("ไม่สามารถสร้างใบส่งเงินสำหรับประเภทหลักประกัน '%s' ได้", self.guarantee_method_id.name))
        vals = {
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "purchase_guarantee_id": self.id,
            "analytic_distribution": self.analytic_distribution,
            "kmitl_payment_type_id": payment_type.id,
            "payment_type": payment_type.direction,
        }
        if payment_type.journal_id:
            vals["journal_id"] = payment_type.journal_id.id
        return vals

    def action_create_payment(self):
        self.ensure_one()

        if self.has_active_payment:
            raise UserError(
                _("This guarantee already has an active payment. A new one cannot be created.")
            )

        vals = self._prepare_account_payment_vals()

        payment = self.env["account.payment"].create(vals)

        self.button_lock()

        # Re-apply analytic distribution after creation.
        # During _inherits creation, AnalyticDistributionMixin's compute
        # resets analytic_distribution before lines are generated.
        if self.analytic_distribution:
            payment.move_id.write(
                {"analytic_distribution": self.analytic_distribution}
            )
            payment.move_id.line_ids.write(
                {"analytic_distribution": self.analytic_distribution}
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
            "target": "current",
        }
