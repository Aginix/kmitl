# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = "/"
        return super().create(vals_list)

    def button_to_verify(self):
        self.ensure_one()
        res = super().button_to_verify()
        if self.name == "/":
            self._assign_document_number()
        return res

    def _assign_document_number(self):
        self.ensure_one()
        fy = self.account_fiscal_year_id
        if not fy:
            raise ValidationError(
                _("Fiscal Year is required to generate the document number.")
            )

        seq_code = f"purchase.request.{fy.name}"
        Sequence = self.env["ir.sequence"].sudo()

        if not Sequence.search([("code", "=", seq_code)], limit=1):
            Sequence.create({
                "name": f"Purchase Request {fy.name}",
                "code": seq_code,
                "prefix": f"PR/{fy.name}/",
                "padding": 4,
                "number_increment": 1,
            })

        self.write({"name": Sequence.next_by_code(seq_code) or "/"})
