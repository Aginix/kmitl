from odoo import _, http
from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class BudgetTransferPortal(CustomerPortal):
    """Customer-portal surface for budget transfers.

    ``/my/budget-transfers`` lists the transfers the logged-in user may read
    (row access is left to the ORM record rules); ``/my/budget-transfer/<id>``
    shows one, with the งปม.303 report served inline / for download through the
    stock ``_show_report`` helper (the same query-param the mixin's
    ``get_portal_url`` appends).
    """

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "budget_transfer_count" in counters:
            Transfer = request.env["budget.transfer"]
            values["budget_transfer_count"] = (
                Transfer.search_count([])
                if Transfer.check_access_rights("read", raise_exception=False)
                else 0
            )
        return values

    @http.route(
        ["/my/budget-transfers", "/my/budget-transfers/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_budget_transfers(self, page=1, sortby=None, **kw):
        Transfer = request.env["budget.transfer"]

        sortings = {
            "date": {"label": _("Date"), "order": "date desc, name desc"},
            "name": {"label": _("Reference"), "order": "name desc"},
            "amount": {"label": _("Amount"), "order": "amount desc"},
        }
        if not sortby:
            sortby = "date"
        order = sortings[sortby]["order"]

        domain = []
        # A logged-in user without budget.transfer model access (e.g. an
        # e-Saraban route participant who reaches a single transfer by direct
        # link) may still land here from the portal home tile — degrade to an
        # empty list instead of raising on search.
        can_read = Transfer.check_access_rights("read", raise_exception=False)
        transfer_count = Transfer.search_count(domain) if can_read else 0
        pager = portal_pager(
            url="/my/budget-transfers",
            url_args={"sortby": sortby},
            total=transfer_count,
            page=page,
            step=self._items_per_page,
        )
        transfers = (
            Transfer.search(
                domain, order=order, limit=self._items_per_page, offset=pager["offset"]
            )
            if can_read
            else Transfer.browse()
        )

        values = {
            # Rendered with sudo: the search above already enforced row-level
            # read rights, so this only reads fields of records the user is
            # entitled to — needed because many display fields are delegated
            # from budget.move (_inherits) which a non-budget reader can't read.
            "transfers": transfers.sudo(),
            "page_name": "budget_transfer",
            "pager": pager,
            "default_url": "/my/budget-transfers",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render(
            "budget_transfer_portal.portal_my_budget_transfers", values
        )

    @http.route(
        ["/my/budget-transfer/<int:transfer_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_budget_transfer(
        self,
        transfer_id=None,
        report_type=None,
        download=False,
        access_token=None,
        **kw
    ):
        try:
            transfer_sudo = self._document_check_access(
                "budget.transfer", transfer_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=transfer_sudo,
                report_type=report_type,
                report_ref="budget_transfer_pdf.action_report_budget_transfer",
                download=download,
            )

        values = self._budget_transfer_get_page_view_values(
            transfer_sudo, access_token, **kw
        )
        return request.render(
            "budget_transfer_portal.portal_budget_transfer_page", values
        )

    def _budget_transfer_get_page_view_values(self, transfer, access_token, **kwargs):
        values = {
            "budget_transfer": transfer,
            "object": transfer,
            "token": access_token,
            "report_type": "pdf",
        }
        return self._get_page_view_values(
            transfer,
            access_token,
            values,
            "my_budget_transfers_history",
            False,
            **kwargs
        )
