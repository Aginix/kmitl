from odoo import api, fields, models


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
    is_transfer = fields.Boolean(
        compute="_compute_is_transfer",
        store=True,
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

    @api.depends("transfer_ids")
    def _compute_is_transfer(self):
        for move in self:
            move.is_transfer = bool(move.transfer_ids)
