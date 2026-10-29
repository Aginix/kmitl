from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    advance_payment_office_ou_ids = fields.Many2many(
        comodel_name="operating.unit",
        relation="res_company_advance_payment_office_ou_rel",
        string="หน่วยงานที่ใช้ flow สำนักงาน",
    )
