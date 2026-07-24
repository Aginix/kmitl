from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ApprovalRequestLine(models.Model):
    """A planned expense line (ค่าใช้จ่าย) — broken down by expense type, not by
    person, and carrying no payee. Who receives the money is decided later, on
    the actual expense allocation (approval.request.allocation)."""

    _name = "approval.request.line"
    _description = "Approval Request Line"
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence")

    request_id = fields.Many2one(
        string="Request",
        comodel_name="approval.request",
        required=True,
        ondelete="cascade",
    )

    allowed_product_ids = fields.Many2many(
        string="Allowed Product IDs",
        compute="_compute_allowed_product_ids",
        comodel_name="product.product",
    )

    product_id = fields.Many2one(
        string="รายการ",
        comodel_name="product.product",
        domain="[('id', 'in', allowed_product_ids)]",
        required=True,
    )

    description = fields.Text(
        string="รายละเอียด",
    )

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        related="request_id.company_id",
    )

    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    total_amount = fields.Monetary(
        string="จำนวนเงิน",
        currency_field="currency_id",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request = self.env["approval.request"].browse(vals.get("request_id"))
            if request and not request.is_plan_editable:
                raise UserError(
                    _("ไม่สามารถเพิ่มรายการค่าใช้จ่ายในสถานะนี้")
                )
        return super().create(vals_list)

    def unlink(self):
        for line in self:
            if not line.request_id.is_plan_editable:
                raise UserError(
                    _("ไม่สามารถลบรายการค่าใช้จ่ายในสถานะนี้")
                )
        return super().unlink()

    @api.depends("request_id.category_id")
    def _compute_allowed_product_ids(self):
        for record in self:
            record.allowed_product_ids = (
                record.request_id.category_id.allowed_product_ids
            )

    @api.constrains("total_amount")
    def _check_total_amount_positive(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise ValidationError(
                    _("จำนวนเงินของรายการค่าใช้จ่าย (แผน) ต้องมากกว่า 0")
                )
