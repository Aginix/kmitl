from odoo import api, fields, models


class ApprovalRequestPayee(models.Model):
    _name = "approval.request.payee"
    _description = "Approval Request Payee"
    _order = "id"

    request_id = fields.Many2one(
        string="Request",
        comodel_name="approval.request",
        required=True,
        ondelete="cascade",
    )

    partner_id = fields.Many2one(
        string="Payee",
        comodel_name="res.partner",
        required=True,
    )

    partner_bank_id = fields.Many2one(
        string="Recipient Bank",
        comodel_name="res.partner.bank",
        domain="[('partner_id', '=', partner_id)]",
    )

    bank_id = fields.Many2one(
        string="Bank",
        comodel_name="res.bank",
        related="partner_bank_id.bank_id",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [v for v in vals_list if v.get("partner_id")]
        if not vals_list:
            return self.browse()
        return super().create(vals_list)

    def _get_masked_acc_number(self):
        self.ensure_one()
        acc = self.partner_bank_id.acc_number or ""
        digit_positions = [i for i, c in enumerate(acc) if c.isdigit()]
        if len(digit_positions) <= 7:
            return acc
        keep = set(digit_positions[:3]) | set(digit_positions[-4:])
        return "".join(
            c if (not c.isdigit() or i in keep) else "X"
            for i, c in enumerate(acc)
        )
