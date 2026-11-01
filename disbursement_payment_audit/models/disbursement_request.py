# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.disbursement_finance_kmitl.models.disbursement_request import (
    AUDITOR_GROUP,
)


class DisbursementRequest(models.Model):
    """The ตรวจจ่าย act: once the bills are posted, the auditor chooses the
    payment subject and checks every payee's banking coordinates. Independent of
    the authorization, which raises the vouchers in disbursement_finance_kmitl."""

    _inherit = "disbursement.request"

    payment_auditor_id = fields.Many2one(
        comodel_name="res.users",
        string="Payment Auditor",
        copy=False,
        readonly=True,
    )
    payment_audit_date = fields.Datetime(
        string="Payment Audited On",
        copy=False,
        readonly=True,
    )

    can_audit_payment = fields.Boolean(compute="_compute_can_audit_payment")

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.audit_payment",
                "name": _lt("Audit Payment"),
                "kind": "act",
                "group": AUDITOR_GROUP,
                "sequence": 60,
                "module": "disbursement_payment_audit",
            }
        ]

    @api.depends("state", "bill_ids.state", "payment_ids.state", "payment_auditor_id")
    @api.depends_context("uid")
    def _compute_can_audit_payment(self):
        """Offered once, until the request is audited (a reset to draft clears
        the stamp) and while no voucher exists: after the authorization raised
        them there is nothing left to audit."""
        for rec in self:
            rec.can_audit_payment = (
                not rec.payment_auditor_id
                and rec._disbursement_act_offered("disbursement.audit_payment")
                and rec._bills_all_posted()
                and not any(payment.state != "cancel" for payment in rec.payment_ids)
            )

    @api.depends("payment_auditor_id")
    def _compute_payment_acts(self):
        """can_edit_payment_subject reads the audit stamp through
        _payment_subject_editable below."""
        return super()._compute_payment_acts()

    def _payment_subject_editable(self):
        """The subject is the auditor's to choose wherever the audit is offered,
        so a station narrows both alike, and only until the audit confirms it:
        changing it re-derives every payee's paying account, which nobody would
        audit again (a reset to draft clears the stamp)."""
        return (
            super()._payment_subject_editable()
            and not self.payment_auditor_id
            and self._disbursement_act_offered("disbursement.audit_payment")
        )

    def action_audit(self):
        """The audit act: check the payees' banking coordinates once the bills
        are posted."""
        for record in self:
            record._disbursement_check_act("disbursement.audit_payment")
            if not record._bills_all_posted():
                raise UserError(_("Post the bills first."))
            record._ensure_payment_lines()
            record._check_payment_classification()
            record.write(
                {
                    "payment_auditor_id": self.env.user.id,
                    "payment_audit_date": fields.Datetime.now(),
                }
            )
            record._stamp_signature("payment_audit")
            record._disbursement_act_done("disbursement.audit_payment")
        return True

    def action_audit_batch(self):
        return self._payment_batch("action_audit", lambda r: r.can_audit_payment)

    def action_draft(self):
        res = super().action_draft()
        self.filtered("payment_auditor_id").write(
            {"payment_auditor_id": False, "payment_audit_date": False}
        )
        return res
