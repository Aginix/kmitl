# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequestSignature(models.Model):
    """One signature on the printed disbursement request — a frozen snapshot of
    who acted at one workflow step.

    The signer's rendered identity (ชื่อ / ตำแหน่ง / ลายเซ็น) is captured the instant
    the step is taken, so a later HR edit — a name correction, a new job title, a
    replaced signature image — never rewrites an already-signed ใบขอเบิก. See
    ADR-0002; the field names deliberately mirror ``sarabun.routing.step`` so the
    two signature blocks on the same page speak one vocabulary.

    Rows are written only by the request's ``_stamp_signature`` under ``sudo``,
    and superseded rows are archived rather than deleted (ADR-0002).
    """

    _name = "disbursement.request.signature"
    _description = "Disbursement Request Signature"
    # The workflow is forward-only, so chronological order is also the canonical
    # role order — no sequence field is needed.
    _order = "signed_date, id"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    step = fields.Selection(
        selection=[
            ("verify", "Verification Officer"),
            ("finance_approve", "Finance Director"),
            ("rector_approve", "Rector-delegated Approver"),
        ],
        string="Step",
        required=True,
        readonly=True,
    )
    signed_by_id = fields.Many2one(
        "res.users", string="Signed By", readonly=True
    )
    signed_date = fields.Datetime(string="Signed On", readonly=True)

    # === Signature snapshot (frozen at signing) ===
    signed_name = fields.Char(
        string="Signer Name (snapshot)", readonly=True, copy=False
    )
    signed_position_name = fields.Char(
        string="Signer Position (snapshot)", readonly=True, copy=False
    )
    signed_signature = fields.Binary(
        string="Signature (snapshot)",
        attachment=True,
        readonly=True,
        copy=False,
    )

    # Superseded rows (a rejected approval re-run, a return to verification) are
    # archived so the PDF prints only the current round while the history stays.
    active = fields.Boolean(default=True)

    signature_image = fields.Binary(
        string="Signature",
        compute="_compute_signature_image",
        help="What the report prints: the snapshot, or the signer's current "
        "employee signature when the snapshot is empty.",
    )

    @api.depends("signed_signature", "signed_by_id")
    def _compute_signature_image(self):
        """Snapshot first, live employee image only as a fallback.

        The fallback covers the real case of someone who acted before uploading
        their signature; a snapshot that exists always wins, so a *replaced*
        image never rewrites a signed request. Read under ``sudo`` for the same
        reason the snapshot is (agx_sarabun ADR-0009): ordinary users cannot read
        another person's ``hr.employee``, and whether the official document shows
        a signature must not depend on who is printing it.
        """
        for record in self:
            record.signature_image = (
                record.signed_signature
                or record.signed_by_id.sudo().employee_id.signature
                or False
            )
