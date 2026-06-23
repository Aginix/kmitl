# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Manager group that may approve / reject entries (step 2: ผู้อนุมัติ).
APPROVER_GROUP = "accounting_kmitl.group_accounting_kmitl_manager"
# Todo pushed to the maker when their entry is rejected.
REJECTED_ACTIVITY = "accounting_kmitl_workflow.mail_activity_move_rejected"
# Todo pushed to the approvers when an entry is submitted for approval.
TO_APPROVE_ACTIVITY = "accounting_kmitl_workflow.mail_activity_move_to_approve"


class AccountMove(models.Model):
    """Add a 2-step maker-checker approval workflow on top of the existing
    draft -> submitted -> posted state machine (defined in accounting_kmitl).

    Step 1 (ผู้จัดทำ/ผู้ตรวจสอบ): Submit -> workflow_state = to_approve.
    Step 2 (ผู้อนุมัติ): Approve -> auto-post immediately.

    The real ``state`` field is unchanged; ``workflow_state`` tracks the
    approval cycle separately and ``display_state`` (computed) merges both for
    the status bar. The gate is enforced at the UI level only (the manual Post
    button is always hidden, posting happens through Approve); system moves that
    call ``_post()`` / ``action_post()`` programmatically are never blocked.
    """

    _inherit = "account.move"

    workflow_state = fields.Selection(
        selection=[
            ("none", "None"),
            ("to_approve", "To Approve"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval",
        default="none",
        copy=False,
        tracking=True,
        index=True,
    )

    display_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("to_approve", "To Approve"),
            ("submitted", "Submitted"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        compute="_compute_display_state",
        store=True,
        copy=False,
    )

    submitted_by = fields.Many2one(
        "res.users", string="Submitted By", copy=False, readonly=True
    )
    submitted_date = fields.Datetime(
        string="Submitted On", copy=False, readonly=True
    )
    approved_by = fields.Many2one(
        "res.users", string="Approved By", copy=False, readonly=True
    )
    approved_date = fields.Datetime(
        string="Approved On", copy=False, readonly=True
    )
    can_submit = fields.Boolean(
        string="Can Submit",
        compute="_compute_can_submit",
        help="Whether the current user may submit this entry: its creator, "
        "or an administrator.",
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("state", "workflow_state")
    def _compute_display_state(self):
        """Merge the real state and the approval workflow into one value for
        the status bar (pattern mirrors disbursement.request.display_status)."""
        for move in self:
            if move.state == "cancel":
                move.display_state = "cancel"
            elif move.state == "posted":
                move.display_state = "posted"
            elif move.state == "submitted":
                move.display_state = (
                    "to_approve"
                    if move.workflow_state == "to_approve"
                    else "submitted"
                )
            else:  # draft (incl. rejected entries reset to draft)
                move.display_state = "draft"

    @api.depends("create_uid")
    @api.depends_context("uid")
    def _compute_can_submit(self):
        """A move may be submitted only by its creator (or an administrator)."""
        is_admin = self.env.is_admin()
        for move in self:
            move.can_submit = is_admin or move.create_uid.id == self.env.uid

    @api.depends("date", "auto_post", "state", "workflow_state")
    def _compute_hide_post_button(self):
        """Always hide the manual Post button: posting happens via Approve."""
        super()._compute_hide_post_button()
        for move in self:
            move.hide_post_button = True

    # ------------------------------------------------------------------
    # Report helper
    # ------------------------------------------------------------------
    def _kmitl_voucher_lines(self):
        """Return the journal items to print (no sections / notes)."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: line.display_type not in ("line_section", "line_note")
        )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Step 1: lock the entry and request approval (ผู้จัดทำ/ผู้ตรวจสอบ).

        Only the creator may submit an entry; administrators may submit any.
        """
        if not self.env.is_admin():
            for move in self:
                if move.create_uid.id != self.env.uid:
                    raise UserError(
                        _("Only the creator of this entry can submit it.")
                    )
        res = super().action_submit()
        self.write(
            {
                "workflow_state": "to_approve",
                "submitted_by": self.env.user.id,
                "submitted_date": fields.Datetime.now(),
                "approved_by": False,
                "approved_date": False,
            }
        )
        # Clear the "rejected" Todo when the maker resubmits a fixed entry.
        self.activity_feedback([REJECTED_ACTIVITY])
        # Push an "to approve" Todo to the approvers.
        self._schedule_approval_todo()
        return res

    def _schedule_approval_todo(self):
        """Push an approval Todo to every approver (manager) for these entries
        so it surfaces in their Todo inbox. Cleared when the entry leaves the
        ``to_approve`` workflow (approve / reject / recall)."""
        approvers = self.env.ref(APPROVER_GROUP).users
        for move in self:
            for approver in approvers - move.submitted_by:
                move.activity_schedule(
                    TO_APPROVE_ACTIVITY,
                    user_id=approver.id,
                    note=move.name or "",
                )

    def action_approve(self):
        """Step 2: approve and post immediately (ผู้อนุมัติ).

        The approver may be the same person as the maker.
        """
        for move in self:
            if move.workflow_state != "to_approve":
                raise UserError(
                    _("Only entries awaiting approval can be approved.")
                )
        self.write(
            {
                "workflow_state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            }
        )
        # The approval is done — clear the approvers' Todo.
        self.activity_feedback([TO_APPROVE_ACTIVITY])
        # Use the public router so payment moves go through
        # account.payment.action_post() (bank-export guard + reconcile) and
        # plain moves through _post().
        self.action_post()
        return True

    def action_approve_batch(self):
        """Approve (and post) many entries at once, isolating failures.

        Each move is approved in its own savepoint so one move that cannot be
        posted (e.g. a payment not yet exported to the bank, an unbalanced
        entry, or insufficient budget) does not roll back the rest. A summary
        notification reports how many were approved and why the others failed.
        """
        candidates = self.filtered(
            lambda move: move.workflow_state == "to_approve"
        )
        approved = self.env["account.move"]
        failures = []
        for move in candidates:
            try:
                with self.env.cr.savepoint():
                    move.action_approve()
                approved |= move
            except (UserError, ValidationError) as error:
                self.env.invalidate_all()
                failures.append(
                    (move.display_name, error.args and error.args[0] or _("error"))
                )
            except Exception as error:  # noqa: BLE001 - isolate per-record failures
                self.env.invalidate_all()
                failures.append((move.display_name, str(error)))

        message = _("%s entry/entries approved.") % len(approved)
        if failures:
            message += "\n" + _("Could not approve:") + "\n"
            message += "\n".join(
                "• %s — %s" % (name, reason) for name, reason in failures
            )
        if failures and not approved:
            notification_type = "danger"
        elif failures:
            notification_type = "warning"
        else:
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Approval"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failures),
            },
        }

    def action_reject(self, reason=None):
        """Reject an entry awaiting approval and send it back to draft."""
        for move in self:
            if move.workflow_state != "to_approve":
                raise UserError(
                    _("Only entries awaiting approval can be rejected.")
                )
        # Keep workflow_state = rejected for history; state goes back to draft.
        self.write({"workflow_state": "rejected", "state": "draft"})
        # The approval is resolved (rejected) — clear the approvers' Todo.
        self.activity_feedback([TO_APPROVE_ACTIVITY])
        body = _("Rejected: %s") % (reason or _("no reason given"))
        for move in self:
            move.message_post(body=body)
            # Push a Todo to the maker so they know the entry is back to them.
            if move.submitted_by:
                move.activity_schedule(
                    REJECTED_ACTIVITY,
                    user_id=move.submitted_by.id,
                    note=reason or _("no reason given"),
                )
        return True

    def action_open_reject_wizard(self):
        """Open the wizard that captures a rejection reason."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Entry"),
            "res_model": "account.move.reject.reason",
            "view_mode": "form",
            # ``views`` is required when the action is opened via orm.call +
            # doAction (call_kw does not run clean_action like call_button does).
            "views": [(False, "form")],
            "target": "new",
            "context": {"active_ids": self.ids, "active_model": "account.move"},
        }

    def action_draft(self):
        """Reset to draft from submitted; doubles as recall (to_approve→draft).

        Only the submitter or an approver may recall an entry under approval.
        """
        for move in self:
            if move.workflow_state == "to_approve" and move.submitted_by:
                if (
                    move.submitted_by != self.env.user
                    and not self.env.user.has_group(APPROVER_GROUP)
                ):
                    raise UserError(
                        _(
                            "Only the submitter or an approver can recall "
                            "this entry."
                        )
                    )
        res = super().action_draft()
        self.write({"workflow_state": "none"})
        # Recalled from approval — remove the approvers' pending Todo.
        self.activity_unlink([TO_APPROVE_ACTIVITY])
        return res

    def button_draft(self):
        """Reset a posted/cancelled move to draft; clear the approval cycle."""
        res = super().button_draft()
        self.write(
            {
                "workflow_state": "none",
                "submitted_by": False,
                "submitted_date": False,
                "approved_by": False,
                "approved_date": False,
            }
        )
        return res
