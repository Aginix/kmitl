from odoo import _, api, fields, models


class AccountingKmitlDashboard(models.AbstractModel):
    """Read-only aggregation service for the accounting landing dashboard.

    Powers the KPI launchpad shown as the first page of the Accounting app.

    Cards are returned as a plain ordered list of self-describing dicts so that
    other modules can add their own card simply by inheriting
    ``get_dashboard_data`` and appending to ``data["cards"]`` -- no front-end
    change is required. Each card is::

        {id, title, color, sequence, res_model, domain, count[, amount]}

    ``amount`` is present only for money cards. The front-end sorts by
    ``sequence`` and opens ``res_model`` / ``domain`` on click, so a card's
    number always matches the list it opens.

    Nothing here uses ``sudo``: record rules scope every figure to what the
    current user may see.
    """

    _name = "accounting.kmitl.dashboard"
    _description = "KMITL Accounting Dashboard"

    _UNPAID_STATES = ("not_paid", "partial")

    @api.model
    def _make_card(self, card_id, title, color, sequence, res_model, domain):
        """Build a count-only KPI card.

        Reusable extension point: modules extending the dashboard with a card
        over their own model should call this instead of hand-building the dict.
        """
        return {
            "id": card_id,
            "title": title,
            "color": color,
            "sequence": sequence,
            "res_model": res_model,
            "domain": domain,
            "count": self.env[res_model].search_count(domain),
        }

    @api.model
    def _residual_card(self, card_id, title, color, sequence, domain):
        """``account.move`` card carrying count + summed ``amount_residual``
        (both come from a single ``read_group``)."""
        groups = self.env["account.move"].read_group(
            domain, ["amount_residual:sum"], []
        )
        return {
            "id": card_id,
            "title": title,
            "color": color,
            "sequence": sequence,
            "res_model": "account.move",
            "domain": domain,
            "count": groups[0]["__count"] if groups else 0,
            "amount": (groups[0]["amount_residual"] if groups else 0.0) or 0.0,
        }

    @api.model
    def get_dashboard_data(self):
        """Return ``{"currency_symbol": str, "cards": [card, ...]}``."""
        uid = self.env.uid
        today = fields.Date.context_today(self)

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

        cards = [
            self._make_card(
                "my_drafts",
                _("My draft documents"),
                "secondary",
                10,
                "account.move",
                [("state", "=", "draft"), ("create_uid", "=", uid)],
            ),
            self._make_card(
                "submitted",
                _("Submitted (awaiting posting)"),
                "info",
                20,
                "account.move",
                [("state", "=", "submitted"), ("create_uid", "=", uid)],
            ),
            self._residual_card(
                "unpaid_ap", _("Unpaid vendor bills"), "warning", 30, unpaid_ap
            ),
            self._residual_card(
                "overdue_ap",
                _("Overdue vendor bills"),
                "danger",
                40,
                unpaid_ap + [("invoice_date_due", "<", today)],
            ),
            self._residual_card(
                "unpaid_ar", _("Unpaid customer invoices"), "primary", 50, unpaid_ar
            ),
            self._make_card(
                "exceptions",
                _("Documents with exceptions"),
                "danger",
                60,
                "account.move",
                [("exception_ids", "!=", False), ("ignore_exception", "=", False)],
            ),
        ]

        return {
            "currency_symbol": self.env.company.currency_id.symbol,
            "cards": cards,
        }

    @api.model
    def get_expense_frequency(self, fiscal_year_id=None, limit=20):
        """Top-N expense accounts ranked by number of distinct posted documents.

        Mirrors the legacy "most-used expense codes" report: for each expense
        account (``account_type == 'expense'`` -- i.e. every KMITL 5xxx code),
        count the *distinct* ``account.move`` that touch it on a posted line,
        optionally within a fiscal year.

        ``read_group`` cannot ``COUNT(DISTINCT ...)``, so we run an aggregate
        query. It still honours record rules (no ``sudo``): the WHERE clause is
        built from the ORM via ``_where_calc`` + ``_apply_ir_rules``, so every
        figure stays scoped to what the current user may see.

        Returns ``{"items": [{id, code, name, count}, ...]}`` sorted desc.
        """
        domain = [
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "expense"),
        ]
        if fiscal_year_id:
            fy = self.env["account.fiscal.year"].browse(fiscal_year_id)
            if fy.exists() and fy.date_from and fy.date_to:
                domain += [("date", ">=", fy.date_from), ("date", "<=", fy.date_to)]

        aml = self.env["account.move.line"]
        aml.flush_model()
        query = aml._where_calc(domain)
        aml._apply_ir_rules(query, "read")
        from_clause, where_clause, params = query.get_sql()
        # ``from_clause`` (not a hard-coded table) is required because record
        # rules may add JOINs; qualify columns to avoid ambiguity. The ``%s``
        # placeholders (from ``where_clause`` and LIMIT) are filled by execute.
        self.env.cr.execute(
            f"""
            SELECT account_move_line.account_id AS account_id,
                   COUNT(DISTINCT account_move_line.move_id) AS doc_count
            FROM {from_clause}
            WHERE {where_clause}
            GROUP BY account_move_line.account_id
            ORDER BY doc_count DESC, account_move_line.account_id
            LIMIT %s
            """,
            params + [limit],
        )
        rows = self.env.cr.dictfetchall()

        accounts = self.env["account.account"].browse(
            [row["account_id"] for row in rows]
        )
        by_id = {account.id: account for account in accounts}
        items = []
        for row in rows:
            account = by_id.get(row["account_id"])
            items.append(
                {
                    "id": row["account_id"],
                    "code": account.code if account else "",
                    "name": account.name if account else "",
                    "count": row["doc_count"],
                }
            )
        return {"items": items}
