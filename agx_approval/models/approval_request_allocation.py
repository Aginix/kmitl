from odoo import api, fields, models


class ApprovalRequestAllocation(models.Model):
    """Actual expense allocation (การจัดสรรค่าใช้จ่ายจริง) — the after-mission
    breakdown recorded on the request: one row per (recipient, expense product,
    actual amount, bank). One row becomes one disbursement line; grouped by
    recipient it is the งบหน้าใบสำคัญคู่จ่าย view. Recipients are drawn from the
    request's participants."""

    _name = "approval.request.allocation"
    _description = "Approval Request Actual Expense Allocation"
    _order = "partner_id, id"

    sequence = fields.Integer(string="Sequence", default=10)

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient",
        required=True,
        domain="[('id', 'in', allowed_recipient_ids)]",
    )

    allowed_recipient_ids = fields.Many2many(
        "res.partner",
        string="Allowed Recipients",
        compute="_compute_allowed_recipient_ids",
    )

    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Recipient Bank",
        domain="[('partner_id', '=', partner_id)]",
    )

    bank_id = fields.Many2one(
        "res.bank",
        string="Bank",
        related="partner_bank_id.bank_id",
        readonly=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Expense",
        domain="[('id', 'in', allowed_product_ids)]",
        required=True,
    )

    allowed_product_ids = fields.Many2many(
        "product.product",
        string="Allowed Products",
        compute="_compute_allowed_product_ids",
    )

    note = fields.Char(string="Description")

    company_id = fields.Many2one(
        "res.company",
        related="request_id.company_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    amount = fields.Monetary(
        string="Actual Amount",
        currency_field="currency_id",
        required=True,
    )

    @api.depends("request_id.participant_ids.partner_id")
    def _compute_allowed_recipient_ids(self):
        for rec in self:
            rec.allowed_recipient_ids = rec.request_id.participant_ids.partner_id

    @api.depends("request_id.category_id")
    def _compute_allowed_product_ids(self):
        for rec in self:
            rec.allowed_product_ids = rec.request_id.category_id.allowed_product_ids

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Default the recipient bank to the partner's first company-scoped
        account, mirroring the old payee-sync behaviour."""
        for rec in self:
            if not rec.partner_id:
                rec.partner_bank_id = False
                continue
            banks = rec.partner_id.bank_ids.filtered(
                lambda b: not b.company_id or b.company_id == rec.company_id
            )
            rec.partner_bank_id = banks[:1].id if banks else False

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
