import logging

from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Purchase_request(models.Model):
    _name = "purchase.request"
    _inherit = "purchase.request"

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    to_create = fields.Selection(
        related="purchase_type_id.to_create",
    )
    procurement_method_ids = fields.Many2many(
        related="purchase_type_id.procurement_method_ids",
    )
    expense_reason = fields.Text(
        string="Reason",
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการตรวจรับพัสดุ",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการกำหนดคุณลักษณะเฉพาะร่างขอบเขตงาน",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการกำหนดราคากลาง",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการพิจารณาผล",
        domain=[("committee_type", "=", "evalutation")],
        copy=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )

    tor_document_ids = fields.One2many(
        "purchase.request.attachment",
        "request_id",
        string="ข้อกำหนดคุณลักษณะ (TOR)",
        domain=[("attachment_type", "=", "tor")],
    )
    rfq_attachment_ids = fields.One2many(
        "purchase.request.attachment",
        "request_id",
        string="ใบเสนอราคา",
        domain=[("attachment_type", "=", "rfq")],
    )
    etc_document_ids = fields.One2many(
        "purchase.request.attachment",
        "request_id",
        string="อื่นๆ",
        domain=[("attachment_type", "=", "etc")],
    )

    title = fields.Text(string="ชื่อเรื่อง")

    source_of_fund = fields.Char(string="แหล่งเงิน")

    plan = fields.Char(string="แผน/งาน/กิจกรรมหลัก/กิจกรรมรอง/ย่อย")

    fund = fields.Char(string="กองทุน")

    budget_type = fields.Char(string="ประเภทงบประมาณ")

    expense_code = fields.Char(string="รหัสค่าใช้จ่าย")

    def _get_domain_purchase_type(self):
        return [("visible_on_purchase_request", "=", True)]

    @api.onchange("purchase_type_id")
    def _onchange_purchase_type_id(self):
        procurement_methods = self.purchase_type_id.procurement_method_ids
        self.update(
            {
                "procurement_method_id": len(procurement_methods) == 1
                and procurement_methods.id
                or False,
            }
        )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            year_buddhist = datetime.today().year + 543
            year_suffix = str(year_buddhist)[-2:]

            seq = self.env['ir.sequence'].next_by_code('purchase.request') or '0000'
            seq_number = seq[-4:]

            vals['name'] = f'PR/{year_suffix}/{seq_number}'
        return super().create(vals)

    @api.constrains('line_ids')
    def _check_product_lines(self):
        for request in self:
            if not request.line_ids:
                raise ValidationError("You must add at least one product line to the Purchase Request.")