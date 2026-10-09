from odoo import api, fields, models


class BudgetMove(models.Model):
    """A budget move is also the ledger posting of a commitment event.

    The header ``move_type`` names the event (``reserve`` / ``obligate`` /
    ``consume``); the bucket each line moves is the line's own ``move_type``
    (ADR-0016). ``res_model``/``res_id`` carry the document that caused the
    event, so "has this document already obligated?" is answered from the
    ledger.
    """

    _inherit = "budget.move"

    move_type = fields.Selection(
        selection_add=[
            ("reserve", "Budget Reservation"),
            ("obligate", "Budget Obligation"),
        ],
        ondelete={"reserve": "cascade", "obligate": "cascade"},
    )
    res_model = fields.Char(
        string="Source Model",
        index=True,
        readonly=True,
        copy=False,
    )
    res_id = fields.Many2oneReference(
        string="Source Document",
        model_field="res_model",
        index=True,
        readonly=True,
        copy=False,
    )

    @api.depends("line_ids.move_type")
    def _compute_amount(self):
        """Total of the lines in the move's own bucket only (ADR-0016, Q6): a
        transfer's reservation top-ups and an event's liquidation lines move
        other buckets and stay out of it, so a transfer still totals 0 and a
        consume move its consumption."""
        for move in self:
            move.total_amount = sum(
                move.line_ids.filtered(
                    lambda line, move_type=move.move_type: line.move_type == move_type
                ).mapped("balance")
            )
