# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import str2bool

# The "To Do" activity raised on a voucher when an officer is assigned.
ASSIGN_ACTIVITY_XMLID = "mail.mail_activity_data_todo"

# ir.config_parameter that relaxes the self-claim guard. Defaults to True:
# because assignment is advisory, an officer may claim a mis-routed voucher
# out of the box. Set to False to lock claims to the assigned officer/manager.
TAKEOVER_PARAM = "finance.allow_takeover_assigned"

OFFICER_GROUP = "finance_kmitl.group_finance_kmitl_user_out"
MANAGER_GROUP = "finance_kmitl.group_finance_kmitl_manager"


class AccountPayment(models.Model):
    """Officer-assignment layer on the payment voucher.

    A voucher is the finance office's from the moment it is created until it is
    paid (``finance_state: draft -> confirmed -> paid``), so that is the span the
    responsible officer carries it for: assigned at creation, released when the
    money is confirmed to have reached the payee. What happens to the voucher
    afterwards belongs to the accounting office and is not routed here.
    """

    _inherit = "account.payment"

    assigned_to = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        copy=False,
        tracking=True,
        index=True,
    )
    # Deliberately outside ``MONEY_FIELDS`` (see finance_kmitl.account_payment):
    # who carries a voucher is not what the bank was told to do, so it stays
    # writable once the voucher is confirmed — which is most of its working life.
    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )

    # -- guards ----------------------------------------------------------
    def _assignment_takeover_allowed(self):
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(TAKEOVER_PARAM, default=True)
        )

    def _assignment_is_manager(self):
        return self.env.user.has_group(MANAGER_GROUP)

    def _assignment_can_claim(self):
        """Whether the current user may self-assign this single voucher."""
        self.ensure_one()
        if not self.assigned_to:
            return True
        if self.assigned_to == self.env.user:
            return False
        return self._assignment_is_manager() or self._assignment_takeover_allowed()

    @api.depends("assigned_to")
    def _compute_assignment_can_assign_me(self):
        for rec in self:
            rec.assignment_can_assign_me = rec._assignment_can_claim()

    # -- activity bookkeeping --------------------------------------------
    def _assignment_activity_summary(self):
        return _("Assigned as responsible finance officer")

    def _assignment_notify(self, user):
        """Raise the assignment To-Do on the voucher itself.

        Not on ``move_id`` the way the hand-over to accounting does: the finance
        office works on the voucher form, the accounting office on the journal
        entry, and each office's To-Do belongs where that office is looking.
        """
        self.ensure_one()
        self.activity_schedule(
            ASSIGN_ACTIVITY_XMLID,
            user_id=user.id,
            summary=self._assignment_activity_summary(),
        )

    def _assignment_clear_activity(self, user):
        """Drop the open assignment to-do previously raised for ``user``."""
        self.ensure_one()
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = self._assignment_activity_summary()
        stale = self.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == activity_type
            and a.summary == summary
        )
        stale.unlink()

    def _assignment_close_activity(self):
        """Close the open assignment to-do(s) once the finance office is done.

        Called when a voucher is paid or cancelled. Uses sudo so the to-do is
        cleared regardless of who performs the action (assignment is not locked,
        so a voucher may be confirmed by another officer — and a request-wide
        confirmation pays every payee at once).
        """
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = self._assignment_activity_summary()
        for rec in self:
            stale = rec.sudo().activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
                and a.summary == summary
            )
            stale.unlink()

    # -- button actions --------------------------------------------------
    def action_assignment_assign_me(self):
        me = self.env.user
        for rec in self:
            if rec.assigned_to == me:
                continue
            if not rec._assignment_can_claim():
                raise UserError(
                    _("This voucher is already assigned to %s.")
                    % rec.assigned_to.display_name
                )
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = me
        return True

    def action_assignment_unassign(self):
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can unassign the officer."))
        for rec in self:
            if rec.assigned_to:
                rec._assignment_clear_activity(rec.assigned_to)
            rec.assigned_to = False
        return True

    def action_assignment_open_wizard(self):
        self.ensure_one()
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can assign another officer."))
        return {
            "name": _("Assign Officer"),
            "type": "ir.actions.act_window",
            "res_model": "finance.assign.officer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payment_id": self.id},
        }

    # -- auto-assign + workflow hooks ------------------------------------
    def _assignment_auto_assign(self):
        """Assign the matching officer to open outbound vouchers and raise a To-Do.

        Vouchers that already carry a responsible officer (manual override, or a
        previous pass over the backlog) keep their officer -- the rules never
        overwrite them. The rule search is sudo'd because a voucher may be created
        by someone outside the finance office (the accounting maker duplicating an
        entry, a scheduled job) and routing must not depend on who happened to
        create it.
        """
        Rule = self.env["finance.assignment.rule"].sudo()
        for rec in self.filtered(
            lambda p: (
                p.payment_type == "outbound"
                and p.finance_state != "paid"
                and p.state != "cancel"
            )
        ):
            if not rec.assigned_to:
                rule = Rule._find_for_payment(rec)
                if not rule:
                    continue
                rec.assigned_to = rule.user_id
            if rec.assigned_to != self.env.user:
                rec._assignment_clear_activity(rec.assigned_to)
                rec._assignment_notify(rec.assigned_to)

    @api.model_create_multi
    def create(self, vals_list):
        """A voucher enters the finance office's queue the moment it exists.

        This is the one door both ways in cover: a voucher filled in by hand on
        the form, and the batch a disbursement request creates for its payees
        (``disbursement.request.action_create_payment``). There is no later
        transition to hang this on -- ``draft`` already *is* the office's work.
        """
        payments = super().create(vals_list)
        payments._assignment_auto_assign()
        return payments

    def _mark_paid(self):
        """The finance office is done with the voucher, so the To-Do is too.

        Hooked here rather than on ``action_confirm_paid`` because this is the
        one road both confirmations take: the voucher's own, and the disbursement
        request's single press that pays every payee at once.
        """
        res = super()._mark_paid()
        self._assignment_close_activity()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._assignment_close_activity()
        return res
