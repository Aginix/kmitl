from odoo import fields, models


class BudgetMove(models.Model):
    """Transfer-facing extension of the core budget move.

    ``budget.transfer`` ``_inherits`` this model 1:1 (account.payment ↔
    account.move pattern, ADR-0013). The two direction-filtered one2many below
    are defined **here**, on ``budget.move`` — their inverse is
    ``budget.move.line.move_id`` — so that ``_inherits`` delegates them onto the
    transfer, giving the transfer form two real FROM/TO boxes over the move's own
    lines without the line ever needing a `transfer_id` back-reference.
    """

    _inherit = "budget.move"

    # Reverse link: which transfer (if any) owns this move. One transfer ⇒ one
    # move, so this is a 0..1 collection. Defined in the feature module, so core
    # `budget.move` stays free of transfer knowledge.
    transfer_ids = fields.One2many(
        comodel_name="budget.transfer",
        inverse_name="move_id",
        string="Budget Transfer",
    )
    # Stamped True once at creation by ``budget.transfer.create`` (delegated
    # through ``_inherits``). The move↔transfer link is a write-once immutable
    # 1:1 (move_id required/readonly/ondelete=cascade, and a transfer mints its
    # own move), so a value set at creation is deterministic — no need to
    # recompute it from ``transfer_ids``.
    is_transfer = fields.Boolean(
        default=False,
        help="True when this move is the ledger entry behind a budget transfer.",
    )

    # FROM (source / credit) and TO (destination / debit) authoring boxes. Same
    # inverse as line_ids (move_id), filtered by transfer_direction; the view
    # sets the per-box context defaults (direction + header department).
    from_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="move_id",
        string="Transfer FROM Lines",
        domain=[("transfer_direction", "=", "from")],
    )
    to_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="move_id",
        string="Transfer TO Lines",
        domain=[("transfer_direction", "=", "to")],
    )

    def action_open_transfer(self):
        """Open the budget transfer that owns this move."""
        self.ensure_one()
        transfer = self.transfer_ids[:1]
        if not transfer:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": transfer.display_name,
            "res_model": "budget.transfer",
            "res_id": transfer.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def get_formview_action(self, access_uid=None):
        """A transfer's ledger move is authored through its ``budget.transfer``
        (ADR-0013) — redirect the internal-link open to the transfer form so
        users edit it there, not on the raw move."""
        self.ensure_one()
        if self.is_transfer:
            return self.action_open_transfer()
        return super().get_formview_action(access_uid=access_uid)
