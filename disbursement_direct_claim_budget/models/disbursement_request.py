# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    """Budget control of a ตั้งเบิกตรง (disbursement ADR-0005).

    A direct claim may still draw a reservation and is then consumed through
    it like any request. Without one it carries its own dimensions and budget
    code, and its consume-budget act posts a direct consumption (ตัดงบตรง, budget
    ADR-0019) that cancelling the request undoes.
    """

    _inherit = "disbursement.request"

    budget_direct_move_id = fields.Many2one(
        "budget.move",
        string="Direct Consumption",
        copy=False,
        readonly=True,
        ondelete="restrict",
    )

    def _action_approve_budget(self):
        self.ensure_one()
        if self.is_direct_claim and not self.budget_commitment_id:
            return self._consume_direct()
        return super()._action_approve_budget()

    def _consume_direct(self):
        """Post a direct consumption for the request's amount on its own
        dimensions and budget code.

        The consume act's role stands in for the Budget-Manager right
        (``budget_direct_consume_by_document``); the pool and dimension checks
        still run on posting, so an exhausted pool aborts the act.
        """
        self.ensure_one()
        # Idempotent across a return-to-verification round trip. Read as sudo:
        # the actor need not hold any budget right.
        if self.sudo().budget_direct_move_id.state == "posted":
            return
        if not self.budget_account_id:
            raise UserError(_("A direct claim needs a budget code before consuming budget."))
        move = self.env["budget.move"].sudo().create(self._prepare_direct_consume_vals())
        move.action_review()
        move.with_context(budget_direct_consume_by_document=True).action_post()
        self.budget_direct_move_id = move
        self.budget_consumed_amount = self.amount_total
        self.budget_consumed_date = fields.Datetime.now()
        self.message_post(
            body=_("Budget consumed directly: %(amount)s (%(move)s)")
            % {"amount": self.amount_total, "move": move.name},
            subtype_xmlid="mail.mt_note",
        )

    def _prepare_direct_consume_vals(self):
        """The direct consumption of this request's amount on its own
        dimensions and budget code — posted by the consume act, checked unsaved on
        Submit."""
        self.ensure_one()
        dims = self.env["budget.controller"]._parse_dimensions(
            self.analytic_distribution
        )
        no_dim = self.env["account.analytic.account"]
        line_dims = {
            column: account.id
            for column, account in dims.items()
            # Related to the move's header on the line.
            if column != "source_analytic_id"
        }
        Move = self.env["budget.move"].sudo()
        vals = {
            "move_type": "consume",
            "budget_type": "expense",
            "ref": self.name,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "company_id": self.company_id.id,
            "department_analytic_id": dims.get("department_analytic_id", no_dim).id,
            "source_analytic_id": dims.get("source_analytic_id", no_dim).id,
            "line_ids": [
                (
                    0,
                    0,
                    dict(
                        line_dims,
                        account_id=self.budget_account_id.id,
                        balance=-self.amount_total,
                    ),
                )
            ],
        }
        # budget_operating_unit would stamp the approver's unit; the
        # consumption belongs to the request's (disbursement_operating_unit),
        # else to its requester's.
        if "operating_unit_id" in Move._fields:
            unit = (
                "operating_unit_id" in self._fields and self.sudo().operating_unit_id
            ) or self.user_id.sudo().default_operating_unit_id
            if unit:
                vals["operating_unit_id"] = unit.id
        return vals

    def _direct_claim_budget_shortfall(self):
        """Whether the pool cannot cover this direct claim without a
        reservation — the Submit pre-check. It runs the posting's own check
        (budget.move.line._check_direct_consume) on the unsaved move, so the
        two cannot disagree; the posting re-checks when the act runs. A
        linked reservation is checked by the act instead."""
        self.ensure_one()
        if self.budget_commitment_id or not self.budget_account_id:
            return False
        move = self.env["budget.move"].sudo().new(self._prepare_direct_consume_vals())
        try:
            move.line_ids._check_direct_consume()
        except UserError:
            return True
        return False

    def _on_cancel(self):
        for rec in self:
            direct = rec.sudo().budget_direct_move_id
            if direct.state == "posted":
                direct.with_context(
                    budget_direct_consume_by_document=True
                ).button_cancel()
                rec.message_post(
                    body=_("Direct consumption %s cancelled.") % direct.name,
                    subtype_xmlid="mail.mt_note",
                )
        # Resets budget_consumed_amount / _date.
        return super()._on_cancel()
