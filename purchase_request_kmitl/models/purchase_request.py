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
    source_of_fund = fields.Char(string="แหล่งเงิน")
    plan = fields.Char(string="แผน/งาน/กิจกรรมหลัก/กิจกรรมรอง/ย่อย")
    fund = fields.Char(string="กองทุน")
    budget_type = fields.Char(string="ประเภทงบประมาณ")
    expense_code = fields.Char(string="รหัสค่าใช้จ่าย")

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
