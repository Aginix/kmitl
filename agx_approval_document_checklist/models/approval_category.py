from odoo import fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    disbursement_document_ids = fields.One2many(
        comodel_name="approval.category.disbursement.document",
        inverse_name="category_id",
        string="เอกสารแนบที่ใช้ในการเบิกจ่าย",
    )
