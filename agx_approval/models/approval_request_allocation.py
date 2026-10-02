from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ApprovalRequestAllocation(models.Model):
    """Actual expense (ค่าใช้จ่ายจริง) — the after-mission record the requester
    enters on the request: one row per (expense product, description, actual
    amount). Carries no recipient, bank or payment type — finance decides those
    on the ใบขอเบิก it creates from the request (ADR-0009)."""

    _name = "approval.request.allocation"
    _description = "Approval Request Actual Expense Allocation"
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence", default=10)

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
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

    # Structural fields cap what finance may bill; once the request leaves the
    # actual-expense phase they may no longer change. Clerical fields stay
    # writable.
    _STRUCTURAL_FIELDS = {
        "request_id",
        "product_id",
        "amount",
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
