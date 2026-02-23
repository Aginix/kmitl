# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class AdvancePaymentPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "advance_payment_count" in counters:
            AdvancePayment = request.env["advance.payment"]
            values["advance_payment_count"] = (
                AdvancePayment.search_count([("owner_id", "=", request.env.user.id)])
                if AdvancePayment.check_access_rights("read", raise_exception=False)
                else 0
            )
        return values

    @http.route(
        ["/my/advance-payments", "/my/advance-payments/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_advance_payments(
        self, page=1, sortby=None, **kw
    ):
        AdvancePayment = request.env["advance.payment"]

        sortings = {
            "date": {"label": "Date", "order": "name desc"},
            "name": {"label": "Reference", "order": "name"},
            "state": {"label": "State", "order": "state"},
        }
        if not sortby:
            sortby = "date"
        order = sortings[sortby]["order"]

        domain = [("owner_id", "=", request.env.user.id)]
        total = AdvancePayment.search_count(domain)

        pager = portal_pager(
            url="/my/advance-payments",
            url_args={"sortby": sortby},
            total=total,
            page=page,
            step=self._items_per_page,
        )

        payments = AdvancePayment.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        values = {
            "payments": payments,
            "page_name": "advance_payment",
            "pager": pager,
            "default_url": "/my/advance-payments",
            "sortings": sortings,
            "sortby": sortby,
        }
        return request.render("advance_payment.portal_my_advance_payments", values)

    @http.route(
        ["/my/advance-payment/<int:payment_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_advance_payment(
        self, payment_id=None, access_token=None, report_type=None, download=False, **kw
    ):
        try:
            payment_sudo = self._document_check_access(
                "advance.payment", payment_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=payment_sudo,
                report_type=report_type,
                report_ref="advance_payment.action_report_advance_payment",
                download=download,
            )

        values = {
            "advance_payment": payment_sudo,
            "object": payment_sudo,
            "token": access_token,
            "report_type": "html",
        }
        values = self._get_page_view_values(
            payment_sudo, access_token, values, "my_advance_payments_history", False, **kw
        )
        return request.render("advance_payment.portal_advance_payment_page", values)
