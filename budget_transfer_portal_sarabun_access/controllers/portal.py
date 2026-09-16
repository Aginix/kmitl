from odoo.addons.budget_transfer_portal.controllers.portal import BudgetTransferPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class BudgetTransferPortalSarabunAccess(BudgetTransferPortal):
    """Grant portal read to a budget transfer's e-Saraban route participants.

    ``budget.transfer`` carries no ``ir.rule`` (budget users see every row via
    model access alone), so a restrictive record rule can't be added without
    also clamping those users — Odoo OR-combines all applicable group rules and
    there is nothing to widen the group back. Instead we open access at the
    controller: an authenticated user who is (or has been) on the linked
    หนังสือ's route may open ``/my/budget-transfer/<id>`` by identity, without
    needing the shared access token. Everything else — the token path, the PDF
    render (sudo), the row-scoped list — is unchanged.
    """

    def _document_check_access(self, model_name, document_id, access_token=None):
        try:
            return super()._document_check_access(
                model_name, document_id, access_token
            )
        except (AccessError, MissingError):
            if model_name == "budget.transfer" and not request.env.user._is_public():
                document_sudo = (
                    request.env[model_name].sudo().browse(document_id).exists()
                )
                if document_sudo and self._budget_transfer_route_reaches_user(
                    document_sudo
                ):
                    return document_sudo
            raise

    def _budget_transfer_route_reaches_user(self, transfer_sudo):
        """True if the current user is a participant of any หนังสือ spawned from
        this transfer — a reached recipient (ADR-0013, spans active + archived
        attempts) or its sender."""
        documents = transfer_sudo.sarabun_document_ids
        participants = documents.mapped("reached_user_ids") | documents.mapped(
            "sender_user_id"
        )
        return request.env.user in participants
