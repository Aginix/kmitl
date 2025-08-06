import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

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

    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการกำหนดคุณลักษณะเฉพาะร่างขอบเขตงาน",
        domain=[("committee_type", "=", "tor_committee")],
        states={'draft': [('readonly', False)]},
        readonly=True,
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการกำหนดราคากลาง",
        domain=[("committee_type", "=", "price_determine")],
        states={'draft': [('readonly', False)]},
        readonly=True,
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการพิจารณาผล",
        domain=[("committee_type", "=", "evaluation")],
        states={'draft': [('readonly', False)]},
        readonly=True,
        copy=True,
    )
    payment_type = fields.Selection([
        ("direct", "จ่ายตรง"),
        ("loan", "เงินยืม"),
        ("prepaid", "สำรองจ่าย")
    ], string="ประเภทการจ่ายเงิน", states={'draft': [('readonly', False)]},
    readonly=True)
    source_of_fund = fields.Char(string="แหล่งเงิน",states={'draft': [('readonly', False)]},
    readonly=True)
    plan = fields.Char(string="แผน/งาน/กิจกรรมหลัก/กิจกรรมรอง/ย่อย",states={'draft': [('readonly', False)]},
    readonly=True)
    fund = fields.Char(string="กองทุน",states={'draft': [('readonly', False)]},
    readonly=True)
    budget_type = fields.Char(string="ประเภทงบประมาณ",states={'draft': [('readonly', False)]},
    readonly=True)
    expense_code = fields.Char(string="รหัสค่าใช้จ่าย",states={'draft': [('readonly', False)]},
    readonly=True)

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

    def button_validation(self):
        return self.write({"state": "validation"})
