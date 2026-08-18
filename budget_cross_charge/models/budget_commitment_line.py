from odoo import _, api, models
from odoo.exceptions import ValidationError


class BudgetCommitmentLine(models.Model):
    _inherit = "budget.commitment.line"

    @api.model_create_multi
    def create(self, vals_list):
        """Manual grid lines on a ถัวจ่าย slip inherit the header dimensions.

        The reservation keeps ONE dimension combination for all its lines
        (ADR 0005/0006) and availability is checked against the header, so a
        line arriving without a distribution (grid row, RPC) is stamped with
        the header's rather than left divergent-by-omission.
        """
        for vals in vals_list:
            if vals.get("analytic_distribution") or not vals.get("commitment_id"):
                continue
            commitment = self.env["budget.commitment"].browse(
                vals["commitment_id"]
            )
            if commitment.is_cross_charge and commitment.analytic_distribution:
                vals["analytic_distribution"] = commitment.analytic_distribution
        return super().create(vals_list)

    @api.constrains("account_id", "move_type", "state")
    def _check_cross_charge(self):
        """A reservation may span >1 budget code only if all are cross-chargeable.

        ถัวจ่าย (ADR 0006): a single reserve line is always allowed; multiple
        reserve lines with *different* budget accounts require every one of
        those accounts to be flagged ``cross_chargeable``. Replaces the core
        constraint, which blocks multiple codes outright.
        """
        for commitment in self.mapped("commitment_id"):
            accounts = commitment.line_ids.filtered(
                lambda l: l.state == "posted" and l.move_type == "reserve"
            ).mapped("account_id")
            if len(accounts) > 1:
                blocked = accounts.filtered(lambda a: not a.cross_chargeable)
                if blocked:
                    raise ValidationError(
                        _(
                            "A reservation may use more than one budget code only "
                            "if every code is marked ถัวจ่ายได้ (cross-chargeable). "
                            "These are not: %s"
                        )
                        % ", ".join(blocked.mapped("display_name"))
                    )
