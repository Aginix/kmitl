# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import format_date, html2plaintext


class GeneralLedgerReportKmitl(models.AbstractModel):
    """General Ledger computed by the OCA engine, extended with KMITL
    accounting-dimension filtering and reshaped for an OWL client action.

    Per account: an opening balance, the period's move lines in date order
    (with a running balance) and a closing balance. The same compute
    (:meth:`get_general_ledger_data`) feeds the on-screen OWL client action
    (called over RPC), the QWeb PDF and the XLSX export, so all three agree.

    Unlike the Trial Balance -- which has to override the OCA domain builders
    because its ``_get_data`` takes no extra-domain argument -- the General
    Ledger engine threads an ``extra_domain`` through both the initial-balance
    and period queries, so the KMITL dimension leaves are injected there.
    """

    _name = "report.accounting_kmitl_reports.general_ledger_kmitl"
    _description = "KMITL General Ledger Report"
    _inherit = [
        "report.account_financial_report.general_ledger",
        "accounting_kmitl_reports.dimension.filter.mixin",
    ]

    # KMITL accounting dimensions shown per line (Account column + expand
    # detail), in display order. Resolved from each move line's
    # ``analytic_distribution`` via its analytic account's ``root_plan_id.code``.
    _GL_DIM_PLANS = ("funds", "departments", "activities", "sources")

    def _get_acc_prt_accounts_ids(self, company_id, grouped_by):
        """This report is always ungrouped (``grouped_by="none"``). The OCA
        engine otherwise forces the partner-grouped path for every
        receivable/payable account, which nests their move lines under
        ``list_grouped`` instead of ``move_lines`` -- so our flat reshape would
        drop them (notably the credit-side lines). Returning no accounts keeps
        every account on the flat ``move_lines`` path."""
        return []

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_general_ledger_data(self, options):
        """Compute the general ledger for ``options`` and return JSON-friendly
        accounts (each with its move lines). Called over RPC by the OWL client
        action and internally by the QWeb/XLSX reports.

        ``options`` keys: ``company_id``, ``date_from``, ``date_to``,
        ``only_posted`` (bool), ``hide_account_at_0`` (bool), ``journal_ids``,
        ``partner_ids``, ``account_ids``, ``account_code_from_id``,
        ``account_code_to_id`` and ``dims`` (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        date_from = options.get("date_from")
        date_to = options.get("date_to")

        if not date_from or not date_to:
            return {"accounts": [], "currency_id": company.currency_id.id}

        currency = company.currency_id
        only_posted = bool(options.get("only_posted", True))
        hide_at_0 = bool(options.get("hide_account_at_0", True))
        journal_ids = options.get("journal_ids") or []
        partner_ids = options.get("partner_ids") or []
        account_ids = list(options.get("account_ids") or [])
        account_ids = self._kmitl_apply_account_range(options, company_id, account_ids)

        # KMITL dimensions (and the optional journal filter) ride along on the
        # engine's extra_domain, which is AND-ed into the period query. The
        # leaves are kept separately because the opening-balance query builds
        # its own domain and must apply exactly the same filters.
        dim_leaves = list(
            self._kmitl_build_dim_leaves(
                options.get("dims") or {}, options.get("dim_only_self")
            )
        )
        extra_domain = list(dim_leaves)
        if journal_ids:
            extra_domain += [("journal_id", "in", journal_ids)]

        # Opening balances are ours, not the OCA engine's: the Trial Balance
        # computes them from the same helper, so the two reports cannot report
        # a different ยอดยกมา for the same account. It also keeps the General
        # Ledger off a private OCA method that upstream reshapes between
        # releases -- which has already silently changed the opening balance of
        # every P&L account on the ``grouped_by="none"`` path we use.
        opening = self._kmitl_opening_balances(
            company_id,
            account_ids,
            self._kmitl_common_ml_domain(
                company_id, journal_ids, partner_ids, only_posted
            )
            + dim_leaves,
            date_from,
            self._kmitl_fy_start_date(date_from, company),
        )
        gen_ld_data = self._kmitl_seed_gen_ld_data(opening)

        # The period lines still come from the OCA engine (a filtered
        # search_read plus its per-account accumulator), seeded with the
        # opening balances above.
        (
            gen_ld_data,
            accounts_data,
            _journals_data,
            _full_reconcile_data,
            _taxes_data,
            _analytic_data,
            rec_after_date_to_ids,
        ) = self._get_period_ml_data(
            account_ids,
            partner_ids,
            company_id,
            False,  # foreign_currency
            only_posted,
            date_from,
            date_to,
            gen_ld_data,
            [],  # cost_center_ids
            extra_domain,
            "none",  # grouped_by
        )
        general_ledger = self._create_general_ledger(
            gen_ld_data, accounts_data, "none", rec_after_date_to_ids, hide_at_0
        )
        general_ledger = sorted(general_ledger, key=lambda a: a["code"] or "")

        # Resolve, in batch, the analytic accounts (for the Account column /
        # dimension detail) and the journal entries (for the expand detail)
        # referenced by every line.
        move_ids, analytic_ids = set(), set()
        for acc in general_ledger:
            for ml in acc.get("move_lines", []):
                if ml.get("entry_id"):
                    move_ids.add(ml["entry_id"])
                for aid in ml.get("analytic_distribution") or {}:
                    analytic_ids.add(int(aid))
        move_map = self._kmitl_move_detail_map(move_ids)
        # Every line of each referenced entry, to resolve the counterpart
        # accounts each selected line faces. They name the Account column and
        # split a line across its counterparts, but never change how much the
        # selected account moved.
        move_lines_map = self._kmitl_move_lines_map(move_ids, company_id)
        cp_account_ids = set()
        for cp_lines in move_lines_map.values():
            for cp in cp_lines:
                if cp["account_id"]:
                    cp_account_ids.add(cp["account_id"][0])
        acc_name = {
            a.id: ("%s %s" % (a.code or "", a.name or "")).strip()
            for a in self.env["account.account"].browse(list(cp_account_ids)).exists()
        }
        ana_map = self._kmitl_analytic_map(analytic_ids)
        dim_labels = {
            "funds": _("Fund"),
            "departments": _("Department"),
            "activities": _("Activity"),
            "sources": _("Source"),
        }

        def build_dimensions(distribution):
            """KMITL dimension chips (expand panel) from an analytic
            distribution, ordered by ``_GL_DIM_PLANS``."""
            by_plan = {}
            for aid in distribution or {}:
                plan, code, name = ana_map.get(int(aid), ("", "", ""))
                if plan:
                    by_plan.setdefault(plan, []).append((code, name))
            dims = []
            for plan in self._GL_DIM_PLANS:
                for code, name in by_plan.get(plan, []):
                    # Display as "[code] name" (e.g. "[0000] ไม่ระบุกองทุน").
                    value = ("[%s] %s" % (code, name)).strip() if code else (name or "")
                    dims.append({"label": dim_labels[plan], "value": value})
            return dims

        accounts = []
        for acc in general_ledger:
            sel_id = acc["id"]
            sel_label = ("%s %s" % (acc["code"] or "", acc["name"] or "")).strip()
            period_debit = 0.0
            period_credit = 0.0
            # Group the selected account's lines per entry, keeping the OCA
            # date order (dict preserves insertion order).
            groups = {}
            for ml in acc.get("move_lines", []):
                period_debit += ml.get("debit") or 0.0
                period_credit += ml.get("credit") or 0.0
                groups.setdefault(ml.get("entry_id"), []).append(ml)

            lines = []
            running = acc["init_bal"]["balance"]
            for entry_id, sel_lines in groups.items():
                detail = move_map.get(entry_id, {})
                cp_lines = move_lines_map.get(entry_id, [])
                # One row per counterpart the selected line faces --
                # the Account column names a real account instead of a
                # catch-all. Splitting is a presentation of the SAME amount:
                # the parts always add back to the line's own debit/credit,
                # so the column totals still tie to the Trial Balance.
                for sel_line in sel_lines:
                    debit = sel_line.get("debit") or 0.0
                    credit = sel_line.get("credit") or 0.0
                    # Side of THIS line, not the entry's net -- an account
                    # posted on both sides of the same entry keeps its own
                    # gross per line instead of collapsing to one side.
                    side = "debit" if debit >= credit else "credit"
                    amount = debit if side == "debit" else credit
                    for cp_label, part in self._kmitl_split_by_counterpart(
                        amount, side, sel_id, sel_label, cp_lines, acc_name, currency
                    ):
                        row_debit = part if side == "debit" else 0.0
                        row_credit = part if side == "credit" else 0.0
                        # Running balance accumulates each displayed row, so
                        # the column always foots (prev +/- this row).
                        running += row_debit - row_credit
                        lines.append(
                            {
                                "date": fields.Date.to_string(sel_line["date"])
                                if sel_line.get("date")
                                else "",
                                "issue": sel_line.get("entry") or "",
                                "entry_id": entry_id or False,
                                # Remark column shows the entry's narration.
                                "narration": detail.get("narration") or "",
                                "maker": detail.get("maker") or "",
                                "maker_date": detail.get("maker_date") or "",
                                "id": "%s-%s-%s-%s"
                                % (sel_id, entry_id, sel_line["id"], len(lines)),
                                "account": cp_label,
                                "debit": row_debit,
                                "credit": row_credit,
                                "balance": running,
                                "dimensions": build_dimensions(
                                    sel_line.get("analytic_distribution")
                                ),
                                "partner": sel_line.get("partner_name") or "",
                            }
                        )

            accounts.append(
                {
                    "id": acc["id"],
                    "code": acc["code"] or "",
                    "name": acc["name"] or "",
                    "initial_balance": acc["init_bal"]["balance"],
                    "period_debit": period_debit,
                    "period_credit": period_credit,
                    # Carried-forward ties to the account's own move lines
                    # (period_debit/period_credit), matching the Trial
                    # Balance -- each row now uses its own line's amount, so
                    # this also equals the sum of the displayed rows.
                    "final_debit": period_debit,
                    "final_credit": period_credit,
                    "final_balance": running,
                    "lines": lines,
                }
            )
        return {"accounts": accounts, "currency_id": company.currency_id.id}

    @api.model
    def _kmitl_split_by_counterpart(
        self, amount, side, sel_id, sel_label, cp_lines, acc_name, currency
    ):
        """Name the counterpart(s) one selected-account line faces, as
        ``[(account_label, part), ...]`` with ``sum(part) == amount``.

        A Thai ledger names the contra account in the Account column, so a
        line settled against several accounts is shown one row per account --
        but only when the entry actually says so. The parts always add back to
        the line's own debit/credit, so Debit/Credit/carried-forward stay equal
        to the account's own move lines and keep tying to the Trial Balance.

        * no counterpart (a same-side-only adjustment) -- one row under the
          selected account's own name;
        * one counterpart -- one row naming it;
        * several whose amounts add up to ``amount`` -- one row each, carrying
          that counterpart's own figure. This is the ordinary case: a single
          line of this account settled against N others, e.g.
          ``Dr เจ้าหนี้ 60,000 / Cr ธนาคาร 59,439.25 / Cr ภาษีหัก ณ ที่จ่าย 560.75``;
        * several that do NOT add up -- one row for the whole amount, labelled
          with every account it faces. The entry pairs no single counterpart to
          this line (two unrelated settlements booked in one move, an account
          posted on both sides, several lines of this account against several
          others), so any split would be invented. Expand the row to see the
          entry as posted.
        """
        totals = {}
        for cp in cp_lines:
            if not cp["account_id"] or cp["account_id"][0] == sel_id:
                continue
            cp_amount = (cp["credit"] if side == "debit" else cp["debit"]) or 0.0
            if cp_amount <= 0:
                continue
            totals[cp["account_id"][0]] = (
                totals.get(cp["account_id"][0], 0.0) + cp_amount
            )
        if not totals:
            return [(sel_label, amount)]
        # Stable, readable order: by account code (acc_name is "code name").
        shares = sorted(
            totals.items(), key=lambda item: acc_name.get(item[0], "") or ""
        )
        if len(shares) == 1:
            return [(acc_name.get(shares[0][0], ""), amount)]
        labels = [acc_name.get(aid, "") for aid, _weight in shares]
        if currency.compare_amounts(sum(w for _aid, w in shares), amount) != 0:
            # Not a clean split of this line -- name them all on one row rather
            # than apportion an amount the entry never recorded.
            return [(", ".join(label for label in labels if label), amount)]
        return list(zip(labels, [weight for _aid, weight in shares]))

    @api.model
    def _kmitl_seed_gen_ld_data(self, opening):
        """Seed the OCA engine's per-account accumulator with KMITL opening
        balances, in the shape ``_get_initial_balance_data`` would have
        returned for ``grouped_by="none"``, no foreign currency and no
        unaffected-earnings account.

        Only ``init_bal["balance"]`` is ever read back (the carried-forward
        totals are recomputed from the account's own move lines), so the
        debit/credit halves stay at zero. Accounts with no opening are added
        by the engine itself as it walks the period lines.
        """
        data = {}
        for account_id, balance in opening.items():
            item = self._initialize_data(False)
            for key_bal in ("init_bal", "fin_bal"):
                item[key_bal]["balance"] = balance
            item["id"] = account_id
            item["none"] = False
            data[account_id] = item
        return data

    @api.model
    def _kmitl_analytic_map(self, analytic_ids):
        """``{analytic_account_id: (root_plan_code, code, name)}`` for the
        accounts referenced by the report's lines."""
        if not analytic_ids:
            return {}
        records = (
            self.env["account.analytic.account"].browse(list(analytic_ids)).exists()
        )
        return {
            a.id: (a.root_plan_id.code or "", a.code or "", a.name or "")
            for a in records
        }

    @api.model
    def _kmitl_move_detail_map(self, move_ids):
        """``{move_id: {narration, maker, maker_date}}`` for the expand detail.
        ``maker`` is the submitter when the workflow module is installed,
        otherwise the entry's creator."""
        if not move_ids:
            return {}
        Move = self.env["account.move"]
        has_submitted = "submitted_by" in Move._fields
        result = {}
        for mv in Move.browse(list(move_ids)).exists():
            if has_submitted and mv.submitted_by:
                maker = mv.submitted_by.display_name
                mdate = mv.submitted_date or mv.date
            else:
                maker = mv.create_uid.display_name
                mdate = mv.create_date or mv.date
            result[mv.id] = {
                "narration": html2plaintext(mv.narration) if mv.narration else "",
                "maker": maker or "",
                "maker_date": fields.Date.to_string(mdate) if mdate else "",
            }
        return result

    @api.model
    def _kmitl_move_lines_map(self, move_ids, company_id):
        """``{move_id: [line_dict, ...]}`` with every posting line of each
        referenced entry (section/note lines excluded). Used only to resolve
        which accounts a selected-account line faces (the Account column) and
        how to divide it between them -- never to drive the amount itself,
        which is always the selected line's own debit/credit."""
        if not move_ids:
            return {}
        rows = self.env["account.move.line"].search_read(
            [
                ("move_id", "in", list(move_ids)),
                ("company_id", "=", company_id),
                ("display_type", "not in", ["line_section", "line_note"]),
            ],
            ["move_id", "account_id", "debit", "credit"],
        )
        result = {}
        for r in rows:
            result.setdefault(r["move_id"][0], []).append(r)
        return result

    @api.model
    def _kmitl_format_amount(self, value):
        """Shared number formatting (kept identical to the OWL side so the PDF
        mirrors the screen). Blank for ~zero to reduce clutter."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    @api.model
    def _kmitl_format_total(self, value):
        """Like :meth:`_kmitl_format_amount` but renders an exact zero as
        ``0.00`` — used by the carried-forward column totals."""
        return "{:,.2f}".format(value or 0.0)

    # ------------------------------------------------------------------
    # PDF / XLSX export — return the report action so the OWL client action
    # can ``doAction`` it. Filters travel in ``data`` so the output mirrors the
    # on-screen report exactly (no persisted record needed).
    # ------------------------------------------------------------------
    def _kmitl_report_action(self, options, report_xmlid):
        options = options or {}
        carrier = self.env["general.ledger.report.wizard.kmitl"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options})

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_general_ledger_kmitl"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_general_ledger_kmitl_xlsx"
        )

    @api.model
    def action_export_csv(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_general_ledger_kmitl_csv"
        )

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute (do NOT call the OCA
    # ``_get_report_values``, which expects the column-based wizard data dict).
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_general_ledger_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "general.ledger.report.wizard.kmitl",
            "docs": self.env["general.ledger.report.wizard.kmitl"].browse(docids or []),
            "res_company": company,
            "accounts": result["accounts"],
            "format_amount": self._kmitl_format_amount,
            "format_total": self._kmitl_format_total,
            "date_from_label": format_date(self.env, options.get("date_from")),
            "date_to_label": format_date(self.env, options.get("date_to")),
        }


class GeneralLedgerXlsxKmitl(models.AbstractModel):
    """XLSX export of the general ledger — shares the compute with the screen
    and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.general_ledger_xlsx"
    _description = "KMITL General Ledger XLSX"
    _inherit = "report.report_xlsx.abstract"

    # Date | Issue | Account | Remark | Debit | Credit | Balance
    _AMOUNT_COLS = (4, 5, 6)

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env["report.accounting_kmitl_reports.general_ledger_kmitl"]
        result = report.get_general_ledger_data(options)
        accounts = result["accounts"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("General Ledger"))
        bold = workbook.add_format({"bold": True})
        head = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#F0F0F0",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        acc_fmt = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        num_bold = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )
        # Zebra-striped variants for alternating data rows (readability).
        cell_alt = workbook.add_format({"border": 1, "bg_color": "#F6F8FA"})
        num_alt = workbook.add_format(
            {"border": 1, "num_format": "#,##0.00", "bg_color": "#F6F8FA"}
        )

        sheet.merge_range(0, 0, 0, 6, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 6, _("General Ledger"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            6,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        headers = [
            _("Date"),
            _("Issue"),
            _("Account"),
            _("Remark"),
            _("Debit"),
            _("Credit"),
            _("Balance"),
        ]
        row_top = 4
        for col, label in enumerate(headers):
            sheet.write(row_top, col, label, head)

        def write_amounts(row_idx, values, fmt, blank_zero=True):
            for col, value in zip(self._AMOUNT_COLS, values):
                if blank_zero and (not value or abs(value) < 0.005):
                    sheet.write_blank(row_idx, col, None, fmt)
                else:
                    sheet.write_number(row_idx, col, value or 0.0, fmt)

        r = row_top + 1
        for acc in accounts:
            sheet.merge_range(
                r, 0, r, 6, "%s - %s" % (acc["code"], acc["name"]), acc_fmt
            )
            r += 1
            # Opening balance (ยอดยกมา)
            sheet.merge_range(r, 0, r, 3, _("Opening Balance"), cell)
            write_amounts(r, [None, None, acc["initial_balance"]], num)
            r += 1
            for idx, line in enumerate(acc["lines"]):
                # Alternate row shading for readability.
                row_cell = cell_alt if idx % 2 else cell
                row_num = num_alt if idx % 2 else num
                sheet.write(r, 0, line["date"], row_cell)
                sheet.write(r, 1, line["issue"], row_cell)
                sheet.write(r, 2, line["account"], row_cell)
                sheet.write(r, 3, line["narration"], row_cell)
                write_amounts(
                    r, [line["debit"], line["credit"], line["balance"]], row_num
                )
                r += 1
            # Closing balance (ยอดยกไป) — totals always shown, even when zero.
            sheet.merge_range(r, 0, r, 3, _("Carried Forward"), num_bold)
            write_amounts(
                r,
                [acc["final_debit"], acc["final_credit"], acc["final_balance"]],
                num_bold,
                blank_zero=False,
            )
            r += 1

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 24)
        sheet.set_column(3, 3, 50)
        sheet.set_column(4, 6, 15)


class GeneralLedgerCsvKmitl(models.AbstractModel):
    """CSV export of the general ledger — one flat row per ledger line, with
    the account code/name repeated on every row (no opening/carried rows), so
    the file is ready for pivot/analysis. Shares the compute with the screen /
    PDF / XLSX."""

    _name = "report.accounting_kmitl_reports.general_ledger_csv"
    _inherit = "accounting_kmitl_reports.csv.report"
    _description = "KMITL General Ledger CSV"

    def _kmitl_csv_rows(self, options):
        report = self.env["report.accounting_kmitl_reports.general_ledger_kmitl"]
        result = report.get_general_ledger_data(options)
        rows = [
            [
                _("Account Code"),
                _("Account Name"),
                _("Date"),
                _("Issue"),
                _("Counterpart Account"),
                _("Partner"),
                _("Remark"),
                _("Debit"),
                _("Credit"),
                _("Balance"),
            ]
        ]
        for acc in result["accounts"]:
            for line in acc["lines"]:
                rows.append(
                    [
                        acc["code"],
                        acc["name"],
                        line["date"],
                        line["issue"],
                        line["account"],
                        line["partner"],
                        line["narration"],
                        self._csv_num(line["debit"]),
                        self._csv_num(line["credit"]),
                        self._csv_num(line["balance"]),
                    ]
                )
        return rows
