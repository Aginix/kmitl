# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Developer-only wizard that re-runs the demo seeding on demand.

``post_init_hook`` only fires on a fresh install, never on ``-u``, so without
this wizard the only way to get another batch of demo data is to rebuild the
database. The wizard reuses the very same story functions the install hooks
call, so there is one code path and no duplicated seeding logic.

Deliberately append-only — see ``README.rst`` for why a wipe cannot be made
sound while the hooks stamp no ``ir.model.data``.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.kmitl_demo.hooks import (
    _create_e2e_purchase_demo,
    _setup_sarabun_org_demo,
)

from ..hooks import seed

_logger = logging.getLogger(__name__)

RUN_COUNT_PARAM = "finance_kmitl_demo.regen_run_count"


class FinanceKmitlDemoRegenWizard(models.TransientModel):
    _name = "finance.kmitl.demo.regen.wizard"
    _description = "Regenerate KMITL Demo Data"

    story_sarabun_org = fields.Boolean(
        string="e-Saraban organisation master data",
        help="Positions, document offices and registers. This story is "
        "idempotent (it searches before creating), so re-running it is safe.",
    )
    story_purchase_e2e = fields.Boolean(
        string="Purchase end-to-end flow",
        help="Purchase requests driven through to purchase orders.",
    )
    story_disbursement = fields.Boolean(
        string="Disbursement flow and vendor bills",
        default=True,
        help="Purchase request through to disbursement request, then vendor "
        "bills created and posted, leaving each request at 'Bills Posted'.",
    )
    story_assets = fields.Boolean(
        string="Fixed assets and depreciation",
        default=True,
        help="Assets built against the KMITL asset profiles, validated and "
        "depreciated for the periods that are already due.",
    )
    run_count = fields.Integer(
        string="Previous manual runs",
        readonly=True,
        default=lambda self: self._default_run_count(),
        help="How many times demo data has already been regenerated from this "
        "wizard on this database. Batches are told apart by their creation "
        "date.",
    )

    @api.model
    def _default_run_count(self):
        return int(
            self.env["ir.config_parameter"].sudo().get_param(RUN_COUNT_PARAM, 0)
        )

    def _selected_stories(self):
        """Return the selected stories as ordered ``(label, runner)`` pairs.

        Ordered so the master data a later story depends on is seeded first.
        The disbursement story and the asset story both live in this module's
        ``seed``, which is why they pass complementary flags instead of being
        called directly.
        """
        self.ensure_one()
        candidates = [
            (
                self.story_sarabun_org,
                _("e-Saraban organisation master data"),
                lambda: _setup_sarabun_org_demo(self.env),
            ),
            (
                self.story_purchase_e2e,
                _("Purchase end-to-end flow"),
                lambda: _create_e2e_purchase_demo(self.env),
            ),
            (
                self.story_disbursement,
                _("Disbursement flow and vendor bills"),
                lambda: seed(self.env, disbursement=True, assets=False),
            ),
            (
                self.story_assets,
                _("Fixed assets and depreciation"),
                lambda: seed(self.env, disbursement=False, assets=True),
            ),
        ]
        return [(label, runner) for selected, label, runner in candidates if selected]

    def action_regenerate(self):
        """Seed the selected stories, each isolated in its own savepoint.

        A savepoint per story rather than a bare ``try``/``except``: the demo
        hooks can raise database-level errors (a duplicate employee, say), and
        those poison the whole transaction, so without one a single bad story
        would take the remaining ones down with it.
        """
        self.ensure_one()
        stories = self._selected_stories()
        if not stories:
            raise UserError(_("Select at least one demo story to regenerate."))

        done = []
        failures = []
        for label, runner in stories:
            try:
                with self.env.cr.savepoint():
                    runner()
                done.append(label)
            except Exception as error:  # noqa: BLE001 - isolate per story
                self.env.invalidate_all()
                _logger.exception("Demo story %r could not be regenerated", label)
                failures.append((label, str(error)))

        if done:
            # Only a run that actually produced records counts as a batch, and
            # the parameter is re-read rather than taken from ``self``: the
            # stored field is frozen at the value the dialog opened with, so a
            # second run in the same dialog would write the same number twice.
            self.env["ir.config_parameter"].sudo().set_param(
                RUN_COUNT_PARAM, self._default_run_count() + 1
            )

        message = _("%s demo story(ies) regenerated.") % len(done)
        if failures:
            # The notification escapes its message and collapses newlines, so
            # failures are separated by a visible marker instead of "\n".
            message += " " + _("Could not regenerate:") + " "
            message += " | ".join(
                "%s — %s" % (label, reason) for label, reason in failures
            )
        if failures and not done:
            notification_type = "danger"
        elif failures:
            notification_type = "warning"
        else:
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Regenerate Demo Data"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failures),
                # Without ``next`` the dialog stays open on a stale counter,
                # which reads as "nothing happened" and invites a second,
                # irreversible run.
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
