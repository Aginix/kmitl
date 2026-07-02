from odoo import api, fields, models


class AccountingKmitlDashboard(models.AbstractModel):
    """Read-only aggregation service for the accounting landing dashboard.

    Powers the KPI launchpad shown as the first page of the Accounting app.
    Every figure is a plain ``search_count`` / ``read_group`` over
    ``account.move``; each card also carries the exact ``domain`` it was built
    from so the front-end can open a matching filtered list on click.

    It never uses ``sudo``: record rules scope every count to what the current
    user may see, so the card number always equals the list opened from it.
    """

    _name = "accounting.kmitl.dashboard"
    _description = "KMITL Accounting Dashboard"

    _UNPAID_STATES = ("not_paid", "partial")

    @api.model
    def get_dashboard_data(self):
        """Return counts (and residual sums) for every KPI card.

        :return: ``{"currency_symbol": str, "cards": {key: {count, [amount],
            domain}}}``
        """
        uid = self.env.uid
        today = fields.Date.context_today(self)
        Move = self.env["account.move"]

        unpaid_ap = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", self._UNPAID_STATES),
        ]
        unpaid_ar = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", self._UNPAID_STATES),
        ]
        # key -> (domain, needs residual sum)
        definitions = {
            "my_drafts": ([("state", "=", "draft"), ("create_uid", "=", uid)], False),
            "submitted": (
                [("state", "=", "submitted"), ("create_uid", "=", uid)],
                False,
            ),
            "unpaid_ap": (unpaid_ap, True),
            "overdue_ap": (unpaid_ap + [("invoice_date_due", "<", today)], True),
            "unpaid_ar": (unpaid_ar, True),
            "exceptions": (
                [("exception_ids", "!=", False), ("ignore_exception", "=", False)],
                False,
            ),
        }

        cards = {}
        for key, (domain, needs_amount) in definitions.items():
            card = {"domain": domain}
            if needs_amount:
                # A single read_group yields both the count and the sum.
                groups = Move.read_group(domain, ["amount_residual:sum"], [])
                card["count"] = groups[0]["__count"] if groups else 0
                card["amount"] = (groups[0]["amount_residual"] if groups else 0.0) or 0.0
            else:
                card["count"] = Move.search_count(domain)
            cards[key] = card

        return {
            "currency_symbol": self.env.company.currency_id.symbol,
            "cards": cards,
        }
