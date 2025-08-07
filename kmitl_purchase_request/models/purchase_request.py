from datetime import datetime

from odoo import api, fields, models


class Purchase_request(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'base.exception']


    _STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("validation", "validation"),
    ("approved", "Approved"),
    ("done", "Done"),
    ("rejected", "Rejected"),
    ]

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )

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
        domain=[("committee_type", "=", "evaluation")],
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

    title = fields.Char(
        string="title",
        required=True
    )

    description = fields.Text(string="เหตุผล/ความจำเป็น", required=True)

    source_of_fund = fields.Char(string="แหล่งเงิน")

    plan = fields.Char(string="แผน/งาน/กิจกรรมหลัก/กิจกรรมรอง/ย่อย")

    fund = fields.Char(string="กองทุน")

    budget_type = fields.Char(string="ประเภทงบประมาณ")

    expense_code = fields.Char(string="รหัสค่าใช้จ่าย")

    payment_type = fields.Selection([
        ("direct", "จ่ายตรง"),
        ("loan", "เงินยืม"),
        ("prepaid", "สำรองจ่าย")
    ])

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        related="requested_by.employee_ids.department_id",
        store=True,
        readonly=True,
    )

    def button_validate(self):
        return self.write({"state": "validation"})

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

    # @api.constrains('line_ids')
    # def _check_product_lines(self):
    #     for request in self:
    #         if not request.line_ids:
    #             raise ValidationError("You must add at least one product line to the Purchase Request.")

    # @api.constrains('work_acceptance_committee_ids', 'tor_committee_ids',
    #                 'price_determine_committee_ids', 'evaluation_committee_ids',
    #                 'estimated_cost')
    # def _check_committee_minimum_members(self):
    #     for record in self:
    #         if record.estimated_cost < 100000:
    #             if len(record.work_acceptance_committee_ids) < 3:
    #                 raise ValidationError(
    #                     f"โครงการมูลค่าต่ำกว่า 100,000: คณะกรรมการตรวจรับพัสดุต้องมีอย่างน้อย 3 คน "
    #                     f"(ปัจจุบันมี {len(record.work_acceptance_committee_ids)} คน)"
    #                 )

    #         elif record.estimated_cost >= 100000:
    #             committees = [
    #                 (record.work_acceptance_committee_ids, 'คณะกรรมการตรวจรับพัสดุ'),
    #                 (record.tor_committee_ids, 'คณะกรรมการกำหนดคุณลักษณะเฉพาะฯ'),
    #                 (record.price_determine_committee_ids, 'คณะกรรมการกำหนดราคากลาง'),
    #                 (record.evaluation_committee_ids, 'คณะกรรมการพิจารณาผล')
    #             ]

    #             for committee, name in committees:
    #                 if len(committee) < 3:
    #                     raise ValidationError(
    #                         f"โครงการมูลค่า 100,000 ขึ้นไป: {name}ต้องมีอย่างน้อย 3 คน "
    #                         f"(ปัจจุบันมี {len(committee)} คน)"
    #                     )
