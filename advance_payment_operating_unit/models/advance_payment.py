from odoo import api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states={"draft": [("readonly", False)]},
        readonly=True,
    )

    # The loan belongs to the borrower's unit, not the drafter's: a loan
    # officer in สนอ. drafting for a faculty member (advance_payment ADR-0031)
    # must not put the request on the Office route or in the wrong OU.
    @api.model
    def _borrower_operating_unit(self, employee):
        # sudo: a drafter without HR rights reads hr.employee.public.
        return employee.sudo().user_id.default_operating_unit_id

    @api.onchange("employee_id")
    def _onchange_employee_id_operating_unit(self):
        unit = self._borrower_operating_unit(self.employee_id)
        if unit:
            self.operating_unit_id = unit

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("employee_id") and "operating_unit_id" not in vals:
                unit = self._borrower_operating_unit(
                    self.env["hr.employee"].browse(vals["employee_id"])
                )
                if unit:
                    vals["operating_unit_id"] = unit.id
        return super().create(vals_list)
