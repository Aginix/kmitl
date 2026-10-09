from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, formatLang


class BudgetTransfer(models.Model):
    """A transfer onto/off a reserved coordinate moves the reservation with it
    (ADR-0016, Q5/Q6).

    A TO line landing on the exact coordinate of an active reservation that owns
    the line's pool tag adds a ``reserve −X`` top-up to the transfer's own move
    (the reservation's cap rises by X); a FROM line out of such a coordinate
    releases ``reserve +X``, never beyond the reservation's unobligated
    remainder. Resetting the posted transfer removes them again.
    """

    _inherit = "budget.transfer"

    def _post_transfer(self):
        commitments = self.env["budget.commitment"]
        for transfer in self:
            commitments |= transfer._ledger_apply_pool_reservations()
        res = super()._post_transfer()
        commitments._check_ledger_limits()
        commitments._sync_state()
        return res

    def action_reset_to_draft(self):
        commitments = self.env["budget.commitment"]
        for transfer in self.filtered(lambda t: t.state == "posted"):
            commitments |= transfer._ledger_unwind_pool_reservations()
        res = super().action_reset_to_draft()
        commitments._check_ledger_limits()
        commitments._sync_state()
        return res

    def _ledger_apply_pool_reservations(self):
        """Add the top-up / release lines; return the reservations touched."""
        self.ensure_one()
        commitments = self.env["budget.commitment"]
        if self.move_id.line_ids.filtered("commitment_line_id"):
            return commitments  # already applied (idempotent re-post)
        free = {}  # unreserved money left per owner's coordinate
        for line in self.line_ids.filtered("transfer_direction"):
            commitment = line._ledger_pool_owner()
            if not commitment:
                continue
            amount = line.amount or 0.0
            if line.transfer_direction == "from":
                # Free money at the coordinate goes first; only the rest is
                # released from the reservation.
                if commitment not in free:
                    free[commitment] = max(line._ledger_free_budget(), 0.0)
                from_free = min(amount, free[commitment])
                free[commitment] -= from_free
                amount -= from_free
                rounding = commitment.currency_id.rounding or 0.01
                if float_compare(amount, 0.0, precision_rounding=rounding) <= 0:
                    continue
                if (
                    float_compare(
                        amount,
                        commitment.available_to_obligate,
                        precision_rounding=rounding,
                    )
                    > 0
                ):
                    raise UserError(
                        _(
                            "Cannot transfer %(amount)s out of reservation %(name)s: "
                            "only %(free)s of it is not yet obligated."
                        )
                        % {
                            "amount": formatLang(
                                self.env, amount, currency_obj=commitment.currency_id
                            ),
                            "name": commitment.display_name,
                            "free": formatLang(
                                self.env,
                                commitment.available_to_obligate,
                                currency_obj=commitment.currency_id,
                            ),
                        }
                    )
                amount = -amount
            commitment._ledger_post_transfer_event(line, amount)
            commitments |= commitment
        return commitments

    def _ledger_unwind_pool_reservations(self):
        """Remove the top-up / release lines before the move is un-posted;
        block when a reservation no longer has a top-up free to give back."""
        self.ensure_one()
        commitments = self.env["budget.commitment"]
        ledger_lines = self.move_id.line_ids.filtered("commitment_line_id")
        for ledger_line in ledger_lines:
            commitment = ledger_line.commitment_id
            amount = -ledger_line.balance  # + top-up, − release
            rounding = commitment.currency_id.rounding or 0.01
            if (
                float_compare(
                    amount,
                    commitment.available_to_obligate,
                    precision_rounding=rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "Cannot reset transfer %(transfer)s: reservation %(name)s "
                        "has already obligated part of the %(amount)s it received "
                        "from this transfer."
                    )
                    % {
                        "transfer": self.display_name,
                        "name": commitment.display_name,
                        "amount": formatLang(
                            self.env, amount, currency_obj=commitment.currency_id
                        ),
                    }
                )
            event = ledger_line.commitment_line_id
            ledger_line.sudo().unlink()
            commitment.sudo().with_context(budget_ledger_posting=True).amount -= amount
            event.sudo().action_cancel()
            commitments |= commitment
        return commitments
