# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

from .report_base import NO_VALUE

REPORT_MODEL = "finance_kmitl_reports.payable.due.report"
CARRIER_MODEL = "finance_kmitl_reports.payable.due.report.wizard"

GROUP_AXES = (
    "invoice_date_due",
    "partner_id",
    "partner_type_id",
    "department_analytic_id",
    "source_analytic_id",
)

ID_FILTERS = (
    ("partner_ids", "partner_id"),
    ("partner_type_ids", "partner_type_id"),
)


class PayableDueReport(models.AbstractModel):
    """รายงานเจ้าหนี้ถึงกำหนดชำระ — what has to be paid, and by when.

    One row per posted vendor bill that is not yet settled, ordered by its due
    date. This looks forward: it is the treasury's schedule of what falls due in
    a coming window, and it is what the office plans an e-payment run against.
    That is a different question from **Aged Payable** in
    ``accounting_kmitl_reports``, which looks backward and buckets what is
    already outstanding by how long it has been outstanding. The two share a
    population and answer opposite questions — see ``CONTEXT.md``.
    """

    _name = REPORT_MODEL
    _inherit = "finance_kmitl_reports.report.base"
    _description = "KMITL Payable Due Report Data Provider"

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_group_axis_titles(self):
        return {
            "invoice_date_due": _("Due Date"),
            "partner_id": _("Vendor"),
            "partner_type_id": _("Partner Type"),
            "department_analytic_id": _("Departments"),
            "source_analytic_id": _("Sources"),
        }

    @api.model
    def get_group_axes(self):
        titles = self._kmitl_group_axis_titles()
        return [{"value": axis, "label": titles[axis]} for axis in GROUP_AXES]

    @api.model
    def get_columns(self):
        return [
            ("invoice_date_due", _("Due Date"), False, 14),
            ("partner", _("Vendor"), False, 30),
            ("partner_type", _("Partner Type"), False, 18),
            ("name", _("Bill No."), False, 20),
            ("invoice_date", _("Bill Date"), False, 14),
            ("ref", _("Vendor Reference"), False, 20),
            ("request", _("Disbursement Request"), False, 18),
            ("amount_total", _("Bill Amount"), True, 16),
            ("amount_residual", _("Amount Due"), True, 16),
            ("days_overdue", _("Days Overdue"), False, 12),
        ]

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_domain(self, options):
        """Everything still owed and falling due on or before ``date_to``.

        ``payment_state`` is borrowed from the accounting dashboard's
        ``_UNPAID_STATES`` rather than restated, so the card the accounting
        office reads every morning and this report cannot disagree about which
        bills are still owed.
        """
        date_to = options["date_to"]
        domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            (
                "payment_state",
                "in",
                list(self.env["accounting.kmitl.dashboard"]._UNPAID_STATES),
            ),
            ("company_id", "=", options.get("company_id") or self.env.company.id),
            ("invoice_date_due", "<=", date_to),
        ]
        if not options.get("include_overdue"):
            domain.append(("invoice_date_due", ">=", options["date_from"]))
        domain = self._kmitl_apply_id_filters(domain, options, ID_FILTERS)
        # account.move is an analytic.mixin in its own right, so the JSON leaf
        # needs no detour the way it does on account.payment.
        return domain + self._kmitl_build_dim_leaves(options.get("dims"))

    @api.model
    def _kmitl_row(self, move, today):
        due = move.invoice_date_due
        days_overdue = (today - due).days if due and due < today else 0
        row = {
            "id": move.id,
            "invoice_date_due": fields.Date.to_string(due) if due else "",
            "partner": move.partner_id.display_name or "",
            "partner_type": move.partner_type_id.display_name or "",
            "name": move.name or "/",
            "invoice_date": (
                fields.Date.to_string(move.invoice_date) if move.invoice_date else ""
            ),
            "ref": move.ref or "",
            "request": move.disbursement_request_id.name or "",
            "amount_total": move.amount_total,
            "amount_residual": move.amount_residual,
            # Blank rather than 0 for a bill that is not late yet: the column is
            # read as an exception list, and a page of zeroes hides the ones
            # that matter.
            "days_overdue": days_overdue or "",
        }
        row["_axes"] = {
            "invoice_date_due": (
                row["invoice_date_due"],
                row["invoice_date_due"] or NO_VALUE,
            ),
            "partner_id": self._kmitl_axis(move.partner_id),
            "partner_type_id": self._kmitl_axis(move.partner_type_id),
            "department_analytic_id": self._kmitl_axis(move.department_analytic_id),
            "source_analytic_id": self._kmitl_axis(move.source_analytic_id),
        }
        return row

    @api.model
    def get_report_data(self, options):
        options = options or {}
        if not options.get("date_from") or not options.get("date_to"):
            return {"groups": [], "grand_total": 0.0}

        moves = self.env["account.move"].search(
            self._kmitl_domain(options), order="invoice_date_due, name"
        )
        today = fields.Date.context_today(self)
        rows = [self._kmitl_row(move, today) for move in moves]

        group_by, group_by_2 = self._kmitl_chosen_axes(
            options, GROUP_AXES, "invoice_date_due"
        )
        # Totalled on the outstanding balance, not on the face value of the
        # bill: a partly-paid bill only still costs what is left of it.
        return self._kmitl_group_rows(rows, group_by, group_by_2, "amount_residual")

    # ------------------------------------------------------------------
    @api.model
    def get_filter_lines(self, options):
        options = options or {}
        lines = []
        if options.get("include_overdue"):
            lines.append(
                _("Due on or before %s, including everything already overdue")
                % (options.get("date_to") or "")
            )
        else:
            lines.append(
                self._kmitl_period_line(
                    _("Due Date"),
                    options.get("date_from"),
                    options.get("date_to"),
                )
            )
        for option_key, title, model in (
            ("partner_ids", _("Vendor"), "res.partner"),
            ("partner_type_ids", _("Partner Type"), "res.partner.type"),
        ):
            line = self._kmitl_record_filter_line(title, model, options.get(option_key))
            if line:
                lines.append(line)
        lines += self._kmitl_dim_filter_lines(options.get("dims"))

        titles = self._kmitl_group_axis_titles()
        group_by, group_by_2 = self._kmitl_chosen_axes(
            options, GROUP_AXES, "invoice_date_due"
        )
        grouping = [titles[group_by]]
        if group_by_2:
            grouping.append(titles[group_by_2])
        lines.append(_("Grouped by: %s") % " › ".join(grouping))
        return lines

    @api.model
    def get_report_note(self):
        return _(
            "Amount Due is what is left of the bill, so a partly-paid bill is "
            "carried at its remaining balance. Days Overdue is counted from "
            "today."
        )

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_payable_due_pdf",
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_payable_due_xlsx",
        )


class PayableDueReportWizard(models.TransientModel):
    _name = CARRIER_MODEL
    _description = "KMITL Payable Due Report Carrier"

    company_id = fields.Many2one("res.company")
    date_from = fields.Date()
    date_to = fields.Date()


class PayableDueReportXlsx(models.AbstractModel):
    _name = "report.finance_kmitl_reports.payable_due_report_xlsx"
    _description = "KMITL Payable Due Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        self.env["finance_kmitl_reports.report.base"]._kmitl_write_xlsx(
            workbook,
            options,
            REPORT_MODEL,
            _("Payables Due"),
            _("Payables Due Report"),
            "amount_residual",
        )


class PayableDueReportPdf(models.AbstractModel):
    _name = "report.finance_kmitl_reports.payable_due_report_pdf"
    _description = "KMITL Payable Due Report PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        options = (data or {}).get("options") or {}
        report = self.env[REPORT_MODEL]
        result = report.get_report_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": CARRIER_MODEL,
            "docs": self.env[CARRIER_MODEL].browse(docids),
            "company": company,
            "columns": report.get_columns(),
            "groups": result.get("groups", []),
            "grand_total": result.get("grand_total", 0.0),
            "filter_lines": report.get_filter_lines(options),
            "report_note": report.get_report_note(),
            "format_amount": report.format_amount,
        }
