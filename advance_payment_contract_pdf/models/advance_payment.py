import logging
import re
from datetime import datetime

from markupsafe import Markup, escape

from odoo import fields, models

from odoo.addons.thai_date_utils.models.thai_date_mixin import MONTHS_TH

_logger = logging.getLogger(__name__)


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def _contract_date_th(self, value):
        """Format a Date/Datetime as a Thai long date for the printed
        contract, e.g. ``23 กรกฎาคม 2569``. Returns "" when empty."""
        if not value:
            return ""
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value)
        return f"{value.day} {MONTHS_TH[value.month]} {value.year + 543}"

    def _contract_thai_distribute(self, text):
        """Markup for a ``.distribute`` paragraph — Thai distributed justify.

        wkhtmltopdf only stretches justified text at spaces, and Thai has no
        spaces between words. So put a space at every Thai word boundary (the
        CSS cancels its width with a negative ``word-spacing``) and wrap the
        real spaces in ``span.rs`` to keep their width: justify then spreads
        each line across all its words and wraps between words, never inside
        one. Same technique as kmitl.project._report_thai_distribute.
        """
        if not text:
            return ""
        try:
            from pythainlp.tokenize import word_tokenize

            tokens = word_tokenize(text, engine="newmm", keep_whitespace=True)
        except ImportError:
            _logger.warning("pythainlp is not installed; Thai text not segmented")
            tokens = [token for token in re.split(r"(\s+)", text) if token]

        def is_thai(char):
            return "\u0e00" <= char <= "\u0e7f" and char not in "ๆฯ"

        out, prev = [], ""
        for token in tokens:
            if token.isspace():
                out.append(Markup('<span class="rs">%s</span>') % token)
                prev = ""
                continue
            if prev and is_thai(prev[-1]) and is_thai(token[0]):
                out.append(" ")
            out.append(escape(token))
            prev = token
        return Markup("").join(out)

    def _contract_sign_steps(self):
        """Signature block → (signer employee, state the signer acts in, date
        stamped by the act). A route extension swaps a block's signer here."""
        self.ensure_one()
        return {
            "borrower": (self.employee_id, "draft", "date_submitted"),
            "endorser": (self.endorser_id.employee_id, "to_endorse", "date_endorsed"),
            "approver": (self.approver_id.employee_id, "to_approve", "date_approved"),
        }

    def _contract_signatures(self):
        """Signer, signature image and date of each signature block on the
        printed contract: ``borrower`` (ผู้ยืม), ``endorser`` (ผู้บังคับบัญชา,
        the เสนอ block), ``approver`` (คำอนุมัติ) and ``receiver`` (the
        borrower again, on ใบรับเงิน — always left to sign and date by hand).

        A block is signed only once the record is past the state its signer
        acts in. The state decides, not the date: ดึงกลับ / ส่งกลับแก้ไข keep
        the old dates, and a cancelled contract prints unsigned. The image is
        the signer's hr.employee signature, read under sudo — the officer who
        prints need not have HR read access. The borrower's block is signed
        only when the borrower submitted personally (ADR-0031)."""
        self.ensure_one()
        rec = self.sudo()
        states = [state for state, _label in self._fields["state"].selection]
        res = {}
        steps = rec._contract_sign_steps()
        for block, (signer, step_state, date_field) in steps.items():
            signed = rec.state != "cancel" and states.index(rec.state) > states.index(
                step_state
            )
            res[block] = {
                "employee": signer,
                "signature": signed and signer.signature,
                "date": signed and self._contract_date_th(rec[date_field]) or "",
            }
        # A loan officer may submit for the borrower (ADR-0031); the borrower's
        # digitised signature then stays off a debt they never confirmed.
        if "borrower" in res and not rec.is_submitted_by_borrower:
            res["borrower"].update(signature=False, date="")
        # The เสนอ block names the role, not the supervisor's own job title.
        if "endorser" in res:
            res["endorser"]["position"] = "ผู้บังคับบัญชา"
        res["receiver"] = {"employee": rec.employee_id, "signature": False, "date": ""}
        return res
