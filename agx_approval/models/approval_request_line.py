from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ApprovalRequestLine(models.Model):
    """A planned expense line (ค่าใช้จ่าย) — carrying no payee. On a category
    with Expense Items it names one of them (or อื่น ๆ with a typed name); on
    any other category the request has exactly one, a bare amount. The unit
    finance disburses against: each ใบขอเบิก line pays one (ADR-0010)."""

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

    expense_item_id = fields.Many2one(
        "approval.category.expense.item",
        string="รายการ",
        ondelete="restrict",
    )

    is_other = fields.Boolean(related="expense_item_id.is_other")

    other_name = fields.Char(
        string="ระบุรายการ",
        help="ชื่อรายการที่ผู้ขอพิมพ์เอง เมื่อเลือก 'อื่น ๆ'",
    )

    name = fields.Char(
        string="ค่าใช้จ่าย",
        compute="_compute_name",
        store=True,
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

    @api.depends(
        "expense_item_id.name", "other_name", "request_id.category_id.name"
    )
    def _compute_name(self):
        for rec in self:
            item = rec.expense_item_id
            if item.is_other:
                rec.name = _("อื่น ๆ: %s") % (rec.other_name or "")
            elif item:
                rec.name = item.name
            else:
                rec.name = rec.request_id.category_id.name

    @api.onchange("expense_item_id")
    def _onchange_expense_item_id(self):
        # The typed name belongs to อื่น ๆ only.
        if not self.expense_item_id.is_other:
            self.other_name = False

    @api.constrains("expense_item_id", "other_name")
    def _check_expense_item(self):
        for rec in self:
            category = rec.request_id.category_id
            if not category.has_expense_items:
                continue
            if not rec.expense_item_id:
                raise ValidationError(
                    _("กรุณาเลือกรายการของค่าใช้จ่ายทุกบรรทัด")
                )
            if rec.expense_item_id.category_id != category:
                raise ValidationError(
                    _("รายการ %s ไม่ใช่รายการของประเภท %s")
                    % (rec.expense_item_id.name, category.name)
                )
            if rec.expense_item_id.is_other and not (rec.other_name or "").strip():
                raise ValidationError(
                    _("กรุณาระบุรายการเมื่อเลือก 'อื่น ๆ'")
                )

    @api.constrains("total_amount")
    def _check_total_amount_positive(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise ValidationError(
                    _("จำนวนเงินของรายการค่าใช้จ่าย (แผน) ต้องมากกว่า 0")
                )
