from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
        string="ผู้รับเงิน",
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
        string="บัญชีธนาคาร",
        domain="[('partner_id', '=', partner_id)]",
    )

    bank_id = fields.Many2one(
        "res.bank",
        string="ธนาคาร",
        related="partner_bank_id.bank_id",
        readonly=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="รายการ",
        domain="[('id', 'in', allowed_product_ids)]",
        required=True,
    )

    allowed_product_ids = fields.Many2many(
        "product.product",
        string="Allowed Products",
        compute="_compute_allowed_product_ids",
    )

    description = fields.Text(string="รายละเอียด")

    payment_type = fields.Selection(
        selection=[
            ("direct", "จ่ายตรง"),
            ("prepaid", "สำรองจ่าย"),
            ("advance", "เงินยืม"),
        ],
        string="ประเภทการจ่ายเงิน",
        required=True,
        default="prepaid",
        help="วิธีที่จ่ายเงินของแถวนี้ — จ่ายตรง/สำรองจ่าย จะเข้าใบเบิก (DR); "
        "เงินยืม จะไม่เข้าใบเบิก แต่ไปเคลียร์กับสัญญายืม (ดู ADR-0002)",
    )

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
        string="จำนวนเงิน",
        currency_field="currency_id",
        required=True,
    )

    # Structural fields drive the disbursement built from this allocation; once
    # the request leaves `actual` they may no longer change (the correction flow
    # only touches the bank — see is_correction). Clerical fields stay writable.
    _STRUCTURAL_FIELDS = {
        "request_id",
        "partner_id",
        "product_id",
        "amount",
        "payment_type",
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request = self.env["approval.request"].browse(vals.get("request_id"))
            if request and not request.is_actual_editable:
                raise UserError(
                    _("ไม่สามารถเพิ่มรายการค่าใช้จ่ายจริงในสถานะนี้")
                )
        return super().create(vals_list)

    def write(self, vals):
        if self._STRUCTURAL_FIELDS & set(vals):
            for rec in self:
                if not rec.request_id.is_actual_editable:
                    raise UserError(
                        _("ไม่สามารถแก้ไขรายการค่าใช้จ่ายจริงในสถานะนี้")
                    )
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if not rec.request_id.is_actual_editable:
                raise UserError(
                    _("ไม่สามารถลบรายการค่าใช้จ่ายจริงในสถานะนี้")
                )
        return super().unlink()

    @api.depends("request_id.participant_ids.partner_id")
    def _compute_allowed_recipient_ids(self):
        for rec in self:
            rec.allowed_recipient_ids = rec.request_id.participant_ids.partner_id

    @api.depends("request_id.line_ids.product_id")
    def _compute_allowed_product_ids(self):
        # Actual-expense products are limited to what the plan (ค่าใช้จ่ายแผน)
        # already lists — you can only settle against a planned expense type.
        for rec in self:
            rec.allowed_product_ids = rec.request_id.line_ids.product_id

    @api.constrains("amount")
    def _check_amount_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(
                    _("จำนวนเงินของค่าใช้จ่ายจริงต้องมากกว่า 0")
                )

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

    def _wht_amount(self):
        """Withholding tax on this row, derived from the recipient's partner
        type (same source the disbursement uses). 0 when the recipient has no
        WHT configured."""
        self.ensure_one()
        wht = self.partner_id.partner_type_id.wht_tax_id
        if wht and self.amount:
            return self.currency_id.round(self.amount * wht.amount / 100.0)
        return 0.0

    def payment_type_label(self):
        """Human label of this row's payment type (จ่ายตรง/สำรองจ่าย/เงินยืม),
        for the disbursement voucher and approval-request reports."""
        self.ensure_one()
        return dict(self._fields["payment_type"].selection).get(
            self.payment_type, ""
        )

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
