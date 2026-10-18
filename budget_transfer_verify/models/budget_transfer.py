from odoo import _, api, fields, models
from odoo.exceptions import UserError

VERIFY_ACTIVITY = "budget_transfer_verify.mail_activity_budget_transfer_verify"
CORRECT_ACTIVITY = "budget_transfer_verify.mail_activity_budget_transfer_correct"


class BudgetTransfer(models.Model):
    """Buddy verification of a confirmed transfer.

    The requester's ยืนยัน still validates the data and mints the BTR number,
    but lands in ``to_verify`` (รอตรวจสอบ) instead of ``submitted``. A Buddy
    covering the transfer's unit (``budget_buddy``) reviews — and may correct —
    the data, then ยืนยันตรวจสอบ moves it on to ``submitted``, the only state
    from which approval (manual approve or the e-Saraban letter) can start. The
    Buddy may instead ส่งกลับแก้ไข (back to draft, with a reason).
    """

    _inherit = "budget.transfer"

    state = fields.Selection(
        selection_add=[("to_verify", "รอตรวจสอบ"), ("submitted",)],
        ondelete={"to_verify": "set default"},
    )

    verifier_id = fields.Many2one(
        string="Buddy ผู้ตรวจสอบ",
        comodel_name="res.users",
        compute="_compute_verifier_id",
        store=True,
        readonly=False,
        copy=False,
        tracking=True,
        domain=lambda self: [
            ("groups_id", "in", self.env.ref("budget_buddy.group_budget_buddy").ids)
        ],
        help="Defaults (in draft) to the primary Buddy from the Buddy settings; "
        "the requester may pick another. Overwritten with whoever actually "
        "verifies.",
    )
    verify_date = fields.Datetime(
        string="วันที่ตรวจสอบ",
        copy=False,
        tracking=True,
        readonly=True,
    )
    show_verify_button = fields.Boolean(compute="_compute_button_visibility")
    show_verify_return_button = fields.Boolean(compute="_compute_button_visibility")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _get_buddies(self):
        """Buddies whose rows match this transfer, primary first. Evaluated
        on demand: a row's domain may read any field, so it cannot sit behind
        a cached compute keyed on the unit alone."""
        self.ensure_one()
        return self.env["budget.buddy"]._get_buddy_users(self)

    def _is_covering_buddy(self):
        """The assigned verifier, or any Buddy the settings match."""
        self.ensure_one()
        user = self.env.user
        return user == self.verifier_id or user in self._get_buddies()

    @api.depends("department_analytic_id", "user_id", "amount")
    def _compute_verifier_id(self):
        """Default the verifier from the Buddy settings while in draft; a
        row's domain may read any field, so the depends cover the usual ones."""
        for transfer in self:
            if transfer.state == "draft":
                transfer.verifier_id = transfer._get_assignable_buddies()[:1]
            else:
                transfer.verifier_id = transfer.verifier_id

    @api.depends("department_analytic_id", "verifier_id")
    @api.depends_context("uid")
    def _compute_can_edit(self):
        """In ``to_verify`` only a covering Buddy (or admin) may edit — the
        requester waits; to change anything they pull the transfer back."""
        super()._compute_can_edit()
        is_admin = self.env.is_admin()
        for transfer in self:
            if transfer.state == "to_verify":
                transfer.can_edit = is_admin or transfer._is_covering_buddy()

    @api.depends("department_analytic_id", "verifier_id")
    @api.depends_context("uid")
    def _compute_button_visibility(self):
        super()._compute_button_visibility()
        user = self.env.user
        is_admin = self.env.is_admin()
        for transfer in self:
            in_verify = transfer.state == "to_verify"
            is_buddy = in_verify and (is_admin or transfer._is_covering_buddy())
            transfer.show_verify_button = is_buddy
            transfer.show_verify_return_button = is_buddy
            if in_verify:
                transfer.show_cancel_button = True
                transfer.show_reset_button = transfer.user_id == user or is_admin

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        """ยืนยัน → ``to_verify``, assigned to the chosen Buddy ผู้ตรวจสอบ.

        Only records the base actually moved to ``submitted`` are re-routed,
        so a ``budget_transfer_exception`` popup (which stops short of the
        base) is left untouched whatever the MRO order. A transfer that skips
        review (``_skip_submit_review``) stays ``submitted``.
        """
        to_review = self.filtered(lambda t: not t._skip_submit_review())
        for transfer in to_review:
            if not transfer.verifier_id:
                raise UserError(
                    _(
                        "กรุณาระบุ Buddy ผู้ตรวจสอบ (ส่วนงาน %s ยังไม่มีเจ้าหน้าที่ Buddy "
                        "ที่มีสิทธิ์เข้าถึงใบโอนนี้ในการตั้งค่า)"
                    )
                    % (transfer.department_analytic_id.display_name or "-")
                )
            if not transfer._buddy_can_read(transfer.verifier_id):
                raise UserError(
                    _("%s ไม่มีสิทธิ์เข้าถึงใบโอนนี้ กรุณาเลือก Buddy ผู้ตรวจสอบคนอื่น")
                    % transfer.verifier_id.name
                )
        res = super().action_submit()
        for transfer in to_review.filtered(lambda t: t.state == "submitted"):
            buddy = transfer.verifier_id
            transfer.write({"state": "to_verify", "verify_date": False})
            transfer.activity_feedback([CORRECT_ACTIVITY])
            transfer.activity_schedule(
                VERIFY_ACTIVITY,
                user_id=buddy.id,
                summary=_("ตรวจสอบการโอนงบประมาณ %s") % transfer.name,
            )
        return res

    def _get_assignable_buddies(self):
        """Covering buddies who can read the transfer, primary first — the
        requester first when they are one (a Buddy verifies their own transfer).

        Coverage is keyed on the unit, not the OU: a buddy the OU rule hides
        the transfer from could not open the To-Do, so they are skipped.
        """
        self.ensure_one()
        buddies = self._get_buddies().filtered(self._buddy_can_read)
        return (buddies & self.user_id) | buddies

    def _buddy_can_read(self, user):
        """Whether ``user``'s record rules let them read this transfer —
        evaluated in memory so it also works on an unsaved record."""
        self.ensure_one()
        domain = self.env["ir.rule"].with_user(user)._compute_domain(self._name)
        return not domain or bool(self.sudo().filtered_domain(domain))

    def _check_can_verify(self):
        is_admin = self.env.is_admin()
        for transfer in self:
            if transfer.state != "to_verify":
                raise UserError(
                    _("Only transfers waiting for verification can be verified.")
                )
            if is_admin:
                continue
            if not transfer._is_covering_buddy():
                raise UserError(
                    _(
                        "Only the assigned Buddy or a Buddy covering %s can verify "
                        "this transfer."
                    )
                    % transfer.department_analytic_id.display_name
                )

    def action_verify(self):
        """ยืนยันตรวจสอบ → ``submitted``. The Buddy may have edited the data,
        so the full confirmation checks run again."""
        self._check_can_verify()
        for transfer in self:
            transfer.invalidate_recordset(
                ["has_sufficient_budget", "budget_validation_message"]
            )
            transfer._validate_transfer_data()
            transfer._validate_budget_availability()
        self.write(
            {
                "state": "submitted",
                "verifier_id": self.env.user.id,
                "verify_date": fields.Datetime.now(),
            }
        )
        self.activity_feedback([VERIFY_ACTIVITY])
        return True

    def action_open_verify_return_wizard(self):
        self.ensure_one()
        self._check_can_verify()
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งกลับแก้ไข"),
            "res_model": "budget.transfer.verify.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transfer_id": self.id},
        }

    def _action_verify_return(self, reason):
        """ส่งกลับแก้ไข: back to draft (number kept) with the Buddy's reason;
        the requester gets a To-Do to correct and re-confirm."""
        self._check_can_verify()
        for transfer in self:
            transfer.message_post(
                body=_("ส่งกลับแก้ไขโดย Buddy: %s") % reason,
                subtype_xmlid="mail.mt_note",
            )
            transfer.activity_feedback([VERIFY_ACTIVITY], feedback=reason)
        self.action_reset_to_draft()
        for transfer in self:
            transfer.activity_schedule(
                CORRECT_ACTIVITY,
                user_id=transfer.user_id.id,
                summary=_("แก้ไขการโอนงบประมาณ %s") % transfer.name,
                note=reason,
            )
        return True

    def action_cancel(self):
        res = super().action_cancel()
        self.activity_unlink([VERIFY_ACTIVITY, CORRECT_ACTIVITY])
        return res

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        self.activity_unlink([VERIFY_ACTIVITY])
        # Keep the verifier: a re-confirmation goes back to the same Buddy.
        self.write({"verify_date": False})
        return res
