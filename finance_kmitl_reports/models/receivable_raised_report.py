# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

from .report_base import NO_VALUE

REPORT_MODEL = "finance_kmitl_reports.receivable.raised.report"
CARRIER_MODEL = "finance_kmitl_reports.receivable.raised.report.wizard"

GROUP_AXES = (
    "invoice_date",
    "partner_id",
    "partner_type_id",
    "department_analytic_id",
    "source_analytic_id",
)

ID_FILTERS = (
    ("partner_ids", "partner_id"),
    ("partner_type_ids", "partner_type_id"),
)


class ReceivableRaisedReport(models.AbstractModel):
    """รายงานการตั้งลูกหนี้ — one row per posted ใบตั้งหนี้ (``out_invoice``),
    on its own วันที่ใบตั้งหนี้.

    A register of debt created, so a row stays whether or not the debt has
    since been paid — what became of it is รายงานลูกหนี้ถึงกำหนดชำระ's
    question, not this one's. account_kmitl archives every other sale journal,
    leaving ใบสำคัญลูกหนี้ as the one AR journal, so ``move_type`` alone is
    enough to scope the population; ``out_refund`` is its own population and
    is never counted here, the same way the payables report never counts
    ``in_refund``.
    """

    _name = REPORT_MODEL
    _inherit = "finance_kmitl_reports.report.base"
    _description = "KMITL Receivable Raised Report Data Provider"

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_group_axis_titles(self):
        return {
            "invoice_date": _("Invoice Date"),
            "partner_id": _("Customer"),
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
            ("invoice_date", _("Invoice Date"), False, 14),
            ("name", _("Invoice No."), False, 20),
            ("partner", _("Customer"), False, 30),
            ("partner_type", _("Partner Type"), False, 18),
            ("ref", _("Customer Reference"), False, 20),
            ("invoice_date_due", _("Due Date"), False, 14),
            ("amount_total", _("Invoice Amount"), True, 16),
            ("amount_residual", _("Amount Due"), True, 16),
        ]

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_domain(self, options):
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", options.get("company_id") or self.env.company.id),
            ("invoice_date", ">=", options["date_from"]),
            ("invoice_date", "<=", options["date_to"]),
        ]
        domain = self._kmitl_apply_id_filters(domain, options, ID_FILTERS)
        # account.move is an analytic.mixin in its own right, so the JSON leaf
        # needs no detour the way it does on account.payment.
        return domain + self._kmitl_build_dim_leaves(options.get("dims"))

    @api.model
    def _kmitl_row(self, move):
        row = {
            "id": move.id,
            "invoice_date": (
                fields.Date.to_string(move.invoice_date) if move.invoice_date else ""
            ),
            "name": move.name or "/",
            "partner": move.partner_id.display_name or "",
            "partner_type": move.partner_type_id.display_name or "",
            "ref": move.ref or "",
            "invoice_date_due": (
                fields.Date.to_string(move.invoice_date_due)
                if move.invoice_date_due
                else ""
            ),
            "amount_total": move.amount_total,
            "amount_residual": move.amount_residual,
        }
        row["_axes"] = {
            "invoice_date": (row["invoice_date"], row["invoice_date"] or NO_VALUE),
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
            self._kmitl_domain(options), order="invoice_date, name"
        )
        rows = [self._kmitl_row(move) for move in moves]

        group_by, group_by_2 = self._kmitl_chosen_axes(
            options, GROUP_AXES, "invoice_date"
        )
        # Totalled on the face value of the invoice, not what remains of it —
        # this report answers "how much debt was raised", which
        # amount_residual only partly reflects. See the due report for the
        # outstanding-balance total.
        return self._kmitl_group_rows(rows, group_by, group_by_2, "amount_total")

    # ------------------------------------------------------------------
    @api.model
    def get_filter_lines(self, options):
        options = options or {}
        lines = [
            self._kmitl_period_line(
                _("Invoice Date"), options.get("date_from"), options.get("date_to")
            )
        ]
        for option_key, title, model in (
            ("partner_ids", _("Customer"), "res.partner"),
            ("partner_type_ids", _("Partner Type"), "res.partner.type"),
        ):
            line = self._kmitl_record_filter_line(title, model, options.get(option_key))
            if line:
                lines.append(line)
        lines += self._kmitl_dim_filter_lines(options.get("dims"))

        titles = self._kmitl_group_axis_titles()
        group_by, group_by_2 = self._kmitl_chosen_axes(
            options, GROUP_AXES, "invoice_date"
        )
        grouping = [titles[group_by]]
        if group_by_2:
            grouping.append(titles[group_by_2])
        lines.append(_("Grouped by: %s") % " › ".join(grouping))
        return lines

    @api.model
    def get_report_note(self):
        return _(
            "Invoice Amount is the full amount raised; Amount Due is what "
            "remains of it, for an invoice that has since been paid in part."
        )

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_receivable_raised_pdf",
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_receivable_raised_xlsx",
        )


class ReceivableRaisedReportWizard(models.TransientModel):
    _name = CARRIER_MODEL
    _description = "KMITL Receivable Raised Report Carrier"

    company_id = fields.Many2one("res.company")
    date_from = fields.Date()
    date_to = fields.Date()


class ReceivableRaisedReportXlsx(models.AbstractModel):
    _name = "report.finance_kmitl_reports.receivable_raised_report_xlsx"
    _description = "KMITL Receivable Raised Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        self.env["finance_kmitl_reports.report.base"]._kmitl_write_xlsx(
            workbook,
            options,
            REPORT_MODEL,
            _("Receivables Raised"),
            _("Receivables Raised Report"),
            "amount_total",
        )


class ReceivableRaisedReportPdf(models.AbstractModel):
    _name = "report.finance_kmitl_reports.receivable_raised_report_pdf"
    _description = "KMITL Receivable Raised Report PDF"

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
