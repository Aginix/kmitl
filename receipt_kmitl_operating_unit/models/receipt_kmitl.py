# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReceiptKmitl(models.Model):
    _inherit = "kmitl.receipt"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
    )

    def _prepare_move_vals(self, line_vals):
        vals = super()._prepare_move_vals(line_vals)
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _prepare_debit_line_vals(self, line):
        vals = super()._prepare_debit_line_vals(line)
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _prepare_deposit_line_vals(self):
        vals_list = super()._prepare_deposit_line_vals()
        if self.operating_unit_id:
            for vals in vals_list:
                vals["operating_unit_id"] = self.operating_unit_id.id
        return vals_list

    def _prepare_move_line_vals(self, line):
        vals = super()._prepare_move_line_vals(line)
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
