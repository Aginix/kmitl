# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo import _, models


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "tier.validation"]

    # Gate ONLY the verified -> approved transition with tier validation.
    # sign/verify keep their existing behaviour (and sarabun coupling).
    _state_from = ["verified"]
    _state_to = ["approved"]
    _tier_validation_manual_config = False

    def _add_tier_validation_buttons(self, node, params):
        """Hide the default Request/Restart/Reevaluate header buttons.

        Reviews are opened automatically on ``action_validate`` and the
        Validate/Reject buttons live in the injected tier label, so hiding
        the header buttons keeps the form clean (mirrors
        ``advance_payment_tier_validation``).
        """
        return etree.Element("div")

    def action_validate(self):
        """Once the officer verifies the request, open the two-tier approval
        by requesting validation so the reviews (Accounting Head -> Finance
        Director) are created automatically.
        """
        res = super().action_validate()
        to_request = self.filtered(
            lambda r: r.state == "verified" and r.need_validation
        )
        if to_request:
            to_request.request_validation()
        return res

    def _validate_tier(self, tiers=False):
        """Approve the disbursement only once BOTH tiers are validated.

        We check ``validation_status == 'validated'`` (all reviews approved)
        rather than "the current user has no more pending review": the two
        reviewers are different people, so the latter would approve
        prematurely right after the first (Accounting Head) tier.

        ``skip_validation_check`` bypasses the tier write-guard so
        ``_action_approve_budget`` can set ``budget_consumed_amount`` while the
        record is still ``verified`` with open reviews.
        """
        super()._validate_tier(tiers)
        for rec in self:
            if rec.state == "verified" and rec.validation_status == "validated":
                rec.with_context(skip_validation_check=True).action_approve()

    def _rejected_tier(self, tiers=False):
        """On rejection at any tier, drop the reviews and send the request back
        to draft for revision (KMITL policy).
        """
        super()._rejected_tier(tiers=tiers)
        for rec in self.filtered(lambda r: r.state == "verified"):
            rec.review_ids.unlink()
            rec.with_context(skip_validation_check=True).write(
                {
                    "state": "draft",
                    "exception_ids": False,
                    "main_exception_id": False,
                    "ignore_exception": False,
                }
            )
            rec.message_post(
                body=_("Approval rejected; returned to draft for revision."),
                subtype_xmlid="mail.mt_note",
            )
