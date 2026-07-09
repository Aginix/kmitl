# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import frozendict, str2bool


class AssignmentMixin(models.AbstractModel):
    """Shared behaviour for documents carrying an Assigned Officer
    (เจ้าหน้าที่ผู้รับผิดชอบ), stored in ``assigned_to``.

    Inheriting this mixin auto-injects the assignment alert (Assign to me /
    Assign… / Unassign) above the form's sheet — mirroring how
    ``base_tier_validation`` injects its label via a ``get_view`` override —
    so consumers never edit their own form XML and the buttons stay out of
    the header's workflow buttons.

    Each consuming model must:
      * also inherit ``mail.activity.mixin`` (which itself brings ``mail.thread``)
        — this mixin deliberately does NOT `_inherit` it (see the note below MRO),
        so the activity API (``activity_schedule`` / ``activity_ids``) is
        expected to come from the consumer's own chain,
      * declare the ``assigned_to`` field (Many2one res.users) — not declared
        here so consumers can keep any pre-existing field's attributes
        untouched (e.g. purchase.request reuses the OCA field), and
      * set the two class-attribute group hooks ``_assign_user_group`` /
        ``_assign_manager_group``.

    Consumers may also override method hooks:
      * ``_assignment_activity_xmlid()`` — use a different mail.activity.type
      * ``_assignment_activity_summary()`` — the To-Do summary shown to users
      * ``_assignment_takeover_param()`` — ir.config_parameter key that toggles
        self-claim of an already-assigned document (None = feature off)
      * ``_assignment_takeover_default()`` — value when the parameter is unset
      * ``_assignment_on_assigned()`` / ``_assignment_on_unassigned()`` —
        lifecycle callbacks invoked after ``assigned_to`` is written

    Class-attribute extension points:
      * ``_assignment_manual_config = False`` — set True to disable the
        auto-injected alert entirely (the Python API stays available)
      * ``_assignment_alert_xpath`` / ``_assignment_alert_position`` — move the
        injected alert to another location in the form
    """

    _name = "assignment.mixin"
    _description = "Assigned Officer (mixin)"
    # Deliberately NOT inheriting mail.thread / mail.activity.mixin here:
    # consumers already inherit them (they need chatter + activities for their
    # own reasons), and adding them again would force a linear MRO across
    # every consumer's chain (portal.mixin, base.exception, budget.commitment.mixin,
    # …) that Python cannot always resolve — for instance disbursement.request:
    #   TypeError: Cannot create a consistent method resolution order (MRO)
    #   for bases mail.thread, mail.activity.mixin, portal.mixin,
    #   budget.commitment.mixin, base.exception, assignment.mixin
    # This mixin uses ``activity_schedule`` / ``activity_ids`` on the *consumer*
    # instance, which are always present because a document worth assigning
    # already has a chatter.

    # Class-attribute hooks (required per consumer)
    _assign_user_group = None  # xmlid of the officer group
    _assign_manager_group = None  # xmlid of the manager group

    # Set True in a consuming model to skip get_view auto-injection while
    # keeping the Python action_* API — for documents that render their own
    # custom banner or don't want any banner at all.
    _assignment_manual_config = False

    # Where the assignment alert lands. Defaults match base_tier_validation's
    # label pattern: xpath at /form/sheet, insert *before*. Consumers may
    # retarget (e.g. "//header" + "inside" to nest it inside the header).
    _assignment_alert_xpath = "/form/sheet"
    _assignment_alert_position = "before"  # "before" | "after" | "inside"

    assignment_can_assign_me = fields.Boolean(
        compute="_compute_assignment_can_assign_me",
    )

    # -- method hooks (optional overrides) -------------------------------
    def _assignment_activity_xmlid(self):
        """xmlid of the mail.activity.type used for assignment notifications.
        Consumers may override to reuse a different type."""
        return "base_assignment.mail_activity_assignment"

    def _assignment_activity_summary(self):
        """Summary shown on the assignment To-Do."""
        return _("Assigned as responsible officer")

    def _assignment_takeover_param(self):
        """ir.config_parameter key that relaxes the self-claim guard. Return
        ``None`` to disable the takeover feature (self-claim only allowed on
        unassigned documents, and reassignment is manager-only)."""
        return None

    def _assignment_takeover_default(self):
        """Default when ``_assignment_takeover_param()`` is unset in the DB."""
        return False

    def _assignment_on_assigned(self, new_user, old_user):
        """Called after ``assigned_to`` is written to a non-empty user (claim,
        wizard, or reassign). Consumers may override to email, log, transition
        a state, etc. Default: no-op."""
        return

    def _assignment_on_unassigned(self, old_user):
        """Called after ``assigned_to`` is cleared (unassign or reassign leaves
        the previous holder). Consumers may override. Default: no-op."""
        return

    # -- guards ----------------------------------------------------------
    def _assignment_takeover_allowed(self):
        param = self._assignment_takeover_param()
        if not param:
            return False
        default = "True" if self._assignment_takeover_default() else "False"
        return str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(param, default=default)
        )

    def _assignment_is_manager(self):
        return self.env.user.has_group(self._assign_manager_group)

    def _assignment_can_claim(self):
        """Whether the current user may self-assign this single record."""
        self.ensure_one()
        if not self.assigned_to:
            return True
        if self.assigned_to == self.env.user:
            return False
        return self._assignment_is_manager() or self._assignment_takeover_allowed()

    @api.depends("assigned_to")
    @api.depends_context("uid")
    def _compute_assignment_can_assign_me(self):
        for rec in self:
            rec.assignment_can_assign_me = rec._assignment_can_claim()

    # -- activity bookkeeping --------------------------------------------
    def _assignment_notify(self, user):
        self.ensure_one()
        self.activity_schedule(
            self._assignment_activity_xmlid(),
            user_id=user.id,
            summary=self._assignment_activity_summary(),
        )

    def _assignment_clear_activity(self, user):
        """Drop the open assignment to-do previously raised for ``user``."""
        self.ensure_one()
        activity_type = self.env.ref(self._assignment_activity_xmlid())
        stale = self.activity_ids.filtered(
            lambda a: a.user_id == user and a.activity_type_id == activity_type
        )
        stale.unlink()

    # -- button actions --------------------------------------------------
    def action_assignment_assign_me(self):
        me = self.env.user
        for rec in self:
            if rec.assigned_to == me:
                continue
            if not rec._assignment_can_claim():
                raise UserError(_(
                    "This document is already assigned to %(user)s."
                ) % {"user": rec.assigned_to.display_name})
            old_user = rec.assigned_to
            if old_user:
                rec._assignment_clear_activity(old_user)
            rec.assigned_to = me
            rec._assignment_on_assigned(me, old_user)
        return True

    def action_assignment_unassign(self):
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can unassign the officer."))
        for rec in self:
            old_user = rec.assigned_to
            if not old_user:
                continue
            rec._assignment_clear_activity(old_user)
            rec.assigned_to = False
            rec._assignment_on_unassigned(old_user)
        return True

    def action_assignment_open_wizard(self):
        self.ensure_one()
        if not self._assignment_is_manager():
            raise AccessError(_("Only a manager can assign another officer."))
        return {
            "name": _("Assign Officer"),
            "type": "ir.actions.act_window",
            "res_model": "assign.officer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    # ------------------------------------------------------------------
    # Auto-inject the assignment alert above the sheet, following the
    # base_tier_validation label pattern (tier_validation.py get_view).
    # ------------------------------------------------------------------
    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return res
        if self._assignment_manual_config:
            # Consumer opted out of the auto-injected banner but still uses
            # the Python API.
            return res
        if not (self._assign_user_group and self._assign_manager_group):
            return res
        doc = etree.XML(res["arch"])
        target_nodes = doc.xpath(self._assignment_alert_xpath)
        if not target_nodes:
            return res
        View = self.env["ir.ui.view"]
        rendered = self.env["ir.qweb"]._render(
            "base_assignment.assignment_buttons_alert",
            {
                "user_group": self._assign_user_group,
                "manager_group": self._assign_manager_group,
            },
        )
        template_node = etree.fromstring(rendered)
        new_arch, new_models = View.postprocess_and_fields(template_node, self._name)
        template_node = etree.fromstring(new_arch)
        position = self._assignment_alert_position
        for target in target_nodes:
            children = list(template_node)
            if position == "after":
                # Iterate reversed so the original document order is preserved.
                for child in reversed(children):
                    target.addnext(child)
            elif position == "inside":
                for child in children:
                    target.append(child)
            else:  # "before" (default)
                for child in children:
                    target.addprevious(child)
        all_models = dict(res["models"])
        for model, view_fields in new_models.items():
            if model in all_models:
                all_models[model] = tuple(set(all_models[model]) | set(view_fields))
            else:
                all_models[model] = tuple(view_fields)
        res["arch"] = etree.tostring(doc)
        res["models"] = frozendict(all_models)
        return res
