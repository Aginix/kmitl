# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChequeRegisterAssignNumbers(models.TransientModel):
    """Number a run of cheques from one starting number.

    The guess only works once the book has been drawn on: a fresh cheque book has
    nothing to guess from, so the first cheque out of it is typed by hand — and
    without this, so is every other cheque in that first batch. Here the officer
    says where the run starts once and the rest follow, which is also what Odoo's
    own ``print.prenumbered.checks`` does for the same reason.

    It doubles as the way to correct a run that started on the wrong number, which
    otherwise means retyping every row.
    """

    _name = "cheque.register.assign.numbers"
    _description = "Number a Run of Cheques"

    cheque_ids = fields.Many2many(
        comodel_name="cheque.register",
        string="Cheques",
        required=True,
        readonly=True,
    )
    cheque_book_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Cheque Book",
        compute="_compute_cheque_book_id",
        help="Numbers run within one book, so a run is numbered within one too.",
    )
    first_number = fields.Char(
        string="First Cheque Number",
        compute="_compute_first_number",
        store=True,
        readonly=False,
        required=True,
        help="The number printed on the first piece of paper in the run. The "
        "rest are counted on from it, keeping the same width.",
    )
    last_number = fields.Char(
        string="Last Cheque Number",
        compute="_compute_last_number",
        help="Where the run ends, so the officer can check it against the book "
        "in their hand before pressing.",
    )

    @api.depends("cheque_ids")
    def _compute_cheque_book_id(self):
        for wizard in self:
            wizard.cheque_book_id = wizard.cheque_ids[:1].cheque_book_id

    @api.depends("cheque_ids")
    def _compute_first_number(self):
        """Start from where the run already starts, then from the guess.

        That order and not the other way round: a run that is already numbered is
        being *re*numbered, and proposing the guess there would offer the number
        after the run rather than the one at the head of it. A run that is blank
        is a fresh book, where the guess has nothing to say either — so the field
        is left empty and the officer types the number off the paper, which is the
        whole reason this wizard exists.

        ``readonly=False`` and stored, so whatever lands here is only a proposal.
        """
        Cheque = self.env["cheque.register"]
        for wizard in self:
            if wizard.first_number:
                continue
            head = wizard.cheque_ids.sorted("id")[:1]
            wizard.first_number = head.cheque_number or Cheque._next_number_for_book(
                head.cheque_book_id
            )

    @api.depends("first_number", "cheque_ids")
    def _compute_last_number(self):
        for wizard in self:
            numbers = wizard._run_numbers(strict=False)
            wizard.last_number = numbers[-1] if numbers else False

    def _run_numbers(self, strict=True):
        """The numbers this run would take, in creation order."""
        self.ensure_one()
        number = self.first_number
        if not number or not number.isdigit():
            if strict:
                raise UserError(
                    _("A cheque number is digits only — %s is not.") % (number or "")
                )
            return []
        Cheque = self.env["cheque.register"]
        numbers = []
        for _cheque in self.cheque_ids.sorted("id"):
            numbers.append(number)
            number = Cheque._bump_number(number)
        return numbers

    def action_assign(self):
        self.ensure_one()
        cheques = self.cheque_ids.sorted("id")
        numbers = self._run_numbers()
        self._check_free(numbers)
        for cheque, number in zip(cheques, numbers):
            cheque.cheque_number = number
        return {"type": "ir.actions.act_window_close"}

    def _check_free(self, numbers):
        """Refuse a run that would land on a number already spent.

        The database constraint would catch it too, one row at a time and after
        the earlier rows had already been written. Named here instead, before
        anything is touched, so the officer is told which number is in the way.
        """
        self.ensure_one()
        clashes = self.env["cheque.register"].search(
            [
                ("id", "not in", self.cheque_ids.ids),
                ("cheque_book_id", "=", self.cheque_book_id.id),
                ("cheque_number", "in", numbers),
            ]
        )
        if clashes:
            raise UserError(
                _(
                    "These numbers have already been spent out of this book: %s. "
                    "A spent number is never handed to a second payee, so start "
                    "the run somewhere else."
                )
                % ", ".join(sorted(clashes.mapped("cheque_number")))
            )
        return True
