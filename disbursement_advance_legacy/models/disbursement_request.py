from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    """A request of payment type เงินยืม (ระบบเก่า) clears a loan made outside
    the system: it names the borrower and the old contract number, pays the
    borrower only, and pays no money out. Not linked to advance.payment."""

    _inherit = "disbursement.request"

    payment_type = fields.Selection(
        selection_add=[("advance_legacy", "เงินยืม (ระบบเก่า)")],
        ondelete={"advance_legacy": "set default"},
    )
    legacy_advance_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="ผู้ยืม",
        index=True,
        copy=False,
        tracking=True,
    )
    legacy_advance_contract_number = fields.Char(
        string="เลขที่สัญญายืมเงิน (ระบบเก่า)",
        index=True,
        copy=False,
        tracking=True,
    )

    @api.depends("payment_type")
    def _compute_pays_out(self):
        res = super()._compute_pays_out()
        self.filtered(lambda r: r.payment_type == "advance_legacy").pays_out = False
        return res

    @api.onchange("payment_type", "partner_type_id")
    def _onchange_has_tax_default(self):
        res = super()._onchange_has_tax_default()
        if (
            self.payment_type == "advance_legacy"
            and self.partner_type_id.company_type != "company"
        ):
            self.has_tax = False
        return res

    @api.onchange("payment_type")
    def _onchange_payment_type_advance_legacy(self):
        if self.payment_type != "advance_legacy":
            self.legacy_advance_employee_id = False
            self.legacy_advance_contract_number = False

    @api.onchange("legacy_advance_employee_id")
    def _onchange_legacy_advance_employee_id(self):
        """The borrower is the only payee."""
        partner = self.legacy_advance_employee_id.work_contact_id
        if not partner:
            return
        if partner.partner_type_id:
            self.partner_type_id = partner.partner_type_id
        if self.line_ids:
            self.line_ids.update({"partner_id": partner.id})
        else:
            self.line_ids = [Command.create({"partner_id": partner.id})]

    @api.constrains(
        "payment_type", "legacy_advance_employee_id", "legacy_advance_contract_number"
    )
    def _check_legacy_advance_payment_type(self):
        for rec in self:
            if rec.payment_type != "advance_legacy" and (
                rec.legacy_advance_employee_id or rec.legacy_advance_contract_number
            ):
                raise ValidationError(
                    _(
                        "Only a request of payment type เงินยืม (ระบบเก่า) may "
                        "name a legacy borrower or contract."
                    )
                )
            rec.line_ids._check_legacy_advance_borrower()

    def action_submit(self):
        for rec in self.filtered(lambda r: r.payment_type == "advance_legacy"):
            if not (
                rec.legacy_advance_employee_id and rec.legacy_advance_contract_number
            ):
                raise UserError(
                    _(
                        "A เงินยืม (ระบบเก่า) request must name the borrower "
                        "and the contract number."
                    )
                )
            if not rec.legacy_advance_employee_id.work_contact_id:
                raise UserError(
                    _(
                        "Borrower %(name)s has no contact to be paid as.",
                        name=rec.legacy_advance_employee_id.name,
                    )
                )
        return super().action_submit()
