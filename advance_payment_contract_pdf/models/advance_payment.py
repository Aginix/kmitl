from datetime import datetime

from odoo import fields, models

from odoo.addons.thai_date_utils.models.thai_date_mixin import MONTHS_TH


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # Signature block → (state its signer acts in, date stamped by the act).
    _CONTRACT_SIGN_STEPS = {
        "borrower": ("draft", "date_submitted"),
        "endorser": ("to_endorse", "date_endorsed"),
        "approver": ("to_approve", "date_approved"),
        "receiver": ("approved", "effective_date"),
    }

    def _contract_date_th(self, value):
        """Format a Date/Datetime as a Thai long date for the printed
        contract, e.g. ``23 กรกฎาคม 2569``. Returns "" when empty."""
        if not value:
            return ""
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value)
        return f"{value.day} {MONTHS_TH[value.month]} {value.year + 543}"

    def _contract_signatures(self):
        """Signer, signature image and date of each signature block on the
        printed contract: ``borrower`` (ผู้ยืม), ``endorser`` (ผู้บังคับบัญชา,
        the เสนอ block), ``approver`` (คำอนุมัติ) and ``receiver`` (the
        borrower again, on ใบรับเงิน once the money is transferred).

        A block is signed only once the record is past the state its signer
        acts in. The state decides, not the date: ดึงกลับ / ส่งกลับแก้ไข keep
        the old dates, and a cancelled contract prints unsigned. The image is
        the signer's hr.employee signature, read under sudo — the officer who
        prints need not have HR read access."""
        self.ensure_one()
        rec = self.sudo()
        states = [state for state, _label in self._fields["state"].selection]
        signers = {
            "borrower": rec.employee_id,
            "endorser": rec.endorser_id.employee_id,
            "approver": rec.approver_id.employee_id,
            "receiver": rec.employee_id,
        }
        res = {}
        for block, (step_state, date_field) in self._CONTRACT_SIGN_STEPS.items():
            signed = rec.state != "cancel" and states.index(rec.state) > states.index(
                step_state
            )
            res[block] = {
                "employee": signers[block],
                "signature": signed and signers[block].signature,
                "date": signed and self._contract_date_th(rec[date_field]) or "",
            }
        return res
