from odoo import api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    is_office_route = fields.Boolean(
        string="Flow สำนักงาน",
        compute="_compute_is_office_route",
        store=True,
        copy=False,
        help="คำขอของหน่วยงานภายใต้สำนักงานอธิการบดี — ไม่ผ่านผู้บังคับบัญชาเห็นชอบ"
        " กำหนดเมื่อส่งคำขอ และไม่เปลี่ยนแม้ภายหลังจะแก้การตั้งค่า (ADR-0027)",
    )

    def _is_office_operating_unit(self):
        self.ensure_one()
        return (
            self.operating_unit_id
            in self.env.company.sudo().advance_payment_office_ou_ids
        )

    @api.depends("operating_unit_id")
    def _compute_is_office_route(self):
        """Follows the OU while in draft only; a submitted request keeps the
        route it was submitted into (snapshotted again in action_submit)."""
        for rec in self:
            if rec.state == "draft":
                rec.is_office_route = rec._is_office_operating_unit()
            else:
                rec.is_office_route = rec.is_office_route

    def _get_route_states(self):
        states = super()._get_route_states()
        office = (
            self._is_office_operating_unit()
            if self.state == "draft"
            else self.is_office_route
        )
        if office:
            states.remove("to_endorse")
        return states

    def action_submit(self):
        # Fix the route now — a Settings change while still in draft must
        # not be missed, and one after submit must not re-route the request.
        # No supervisor on this route: clear the suggested endorser so the
        # endorser record rules grant nobody access to the request.
        for rec in self.filtered(lambda r: r.state == "draft"):
            rec.is_office_route = rec._is_office_operating_unit()
            if rec.is_office_route:
                rec.endorser_id = False
        return super().action_submit()

    def _contract_sign_steps(self):
        """No supervisor on the Office route: the director's review fills the
        เสนอ block in the supervisor's place."""
        steps = super()._contract_sign_steps()
        if self.is_office_route:
            steps["endorser"] = (
                self.director_id.employee_id,
                "to_director",
                "date_director_reviewed",
            )
        return steps
