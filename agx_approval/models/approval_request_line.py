from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ApprovalRequestLine(models.Model):
    _name = "approval.request.line"
    _description = "Approval Request Line"

    sequence = fields.Integer(
        string="Sequence"
    )

    request_id = fields.Many2one(
        string="Request",
        comodel_name="approval.request",
        required=True
    )

    partner_id = fields.Many2one(
        string="Payee",
        comodel_name="res.partner",
        domain="[('partner_type_id', 'in', allowed_partner_type_ids)]"
        " if allowed_partner_type_ids else []",
        required=True
    )

    allowed_product_ids = fields.Many2many(
        string='Allowed Product IDs',
        compute='_compute_allowed_product_ids',
        comodel_name="product.product"
    )

    allowed_partner_type_ids = fields.Many2many(
        string="Allowed Partner Types",
        compute="_compute_allowed_partner_type_ids",
        comodel_name="res.partner.type",
    )

    product_id = fields.Many2one(
        string="Expense",
        comodel_name="product.product",
        domain="[('id', 'in', allowed_product_ids)]",
        required=True
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
        string="Requested Amount",
        currency_field='currency_id',
        required=True,
    )

    actual_amount = fields.Monetary(
        string="Actual Amount",
        currency_field="currency_id",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request = self.env["approval.request"].browse(vals.get("request_id"))
            if request and request.state == "approved":
                raise UserError(_("ไม่สามารถเพิ่มรายการเมื่อใบคำขออยู่ในสถานะ Approved"))
        return super().create(vals_list)

    def unlink(self):
        for line in self:
            if line.request_id.state == "approved":
                raise UserError(_("ไม่สามารถลบรายการเมื่อใบคำขออยู่ในสถานะ Approved"))
        return super().unlink()

    @api.depends('request_id.category_id')
    def _compute_allowed_product_ids(self):
        for record in self:
            record.allowed_product_ids = record.request_id.category_id.allowed_product_ids

    @api.depends(
        "request_id.category_id.allow_internal_partner",
        "request_id.category_id.allow_external_partner",
        "request_id.category_id.allow_student_partner",
    )
    def _compute_allowed_partner_type_ids(self):
        for record in self:
            category = record.request_id.category_id
            types = self.env["res.partner.type"]
            if category.allow_internal_partner:
                types |= self.env.ref("partner_type_aginix.partner_type_employee")
            if category.allow_external_partner:
                types |= self.env.ref("partner_type_aginix.partner_type_other")
                types |= self.env.ref("partner_type_aginix.partner_type_company")
            if category.allow_student_partner:
                types |= self.env.ref("partner_type_aginix.partner_type_student")
            record.allowed_partner_type_ids = types

    def _get_payee_bank(self):
        self.ensure_one()
        payee = self.request_id.payee_ids.filtered(
            lambda p: p.partner_id == self.partner_id
        )[:1]
        return payee.partner_bank_id
