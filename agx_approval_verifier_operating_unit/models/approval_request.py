from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.agx_approval_verifier.models.approval_request import VERIFY_GROUP


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # res.users carries no OU rule, so scope the picker to verifiers assigned to
    # the request's OU. A string domain lets the client evaluate
    # operating_unit_id; it filters on the stored assigned_operating_unit_ids
    # because the computed operating_unit_ids is not searchable.
    verifier_id = fields.Many2one(
        domain=lambda self: (
            "[('groups_id', 'in', %s), "
            "('assigned_operating_unit_ids', 'in', operating_unit_id)]"
            % self.env.ref(VERIFY_GROUP).ids
        ),
    )

    def _verifier_outside_operating_unit(self):
        self.ensure_one()
        return (
            self.verifier_id
            and self.operating_unit_id
            and self.operating_unit_id
            not in self.verifier_id.sudo().assigned_operating_unit_ids
        )

    @api.model
    def _verifier_default_domain(self):
        return super()._verifier_default_domain() + [
            (
                "operating_unit_id",
                "=",
                self.env["res.users"].operating_unit_default_get().id,
            )
        ]

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit_id_verifier(self):
        # Guarded: Odoo runs every onchange on a new record's first pass, so only
        # clear a verifier that really falls outside the OU.
        if self._verifier_outside_operating_unit():
            self.verifier_id = False

    @api.constrains("verifier_id", "operating_unit_id")
    def _check_verifier_operating_unit(self):
        for rec in self:
            if rec._verifier_outside_operating_unit():
                raise ValidationError(
                    _(
                        "ผู้ตรวจสอบที่ระบุ %(user)s ไม่ได้อยู่ในหน่วยปฏิบัติงาน %(ou)s ของคำขอ",
                        user=rec.verifier_id.name,
                        ou=rec.operating_unit_id.name,
                    )
                )
