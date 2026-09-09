# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

from .report_base import NO_VALUE

REPORT_MODEL = "finance_kmitl_reports.payment.report"
CARRIER_MODEL = "finance_kmitl_reports.payment.report.wizard"

# The axes the officer may fold the report by, on either level. Anything the
# report already shows a column for, plus the two dimensions the office asks
# "how much went out of this money" with.
GROUP_AXES = (
    "paid_date",
    "payment_method_line_id",
    "payment_method_id",
    "source_analytic_id",
    "department_analytic_id",
    "kmitl_payment_subject_id",
    "partner_id",
)

# Control-panel picker -> the payment field it narrows.
ID_FILTERS = (
    ("paying_account_ids", "payment_method_line_id"),
    ("method_ids", "payment_method_id"),
    ("partner_ids", "partner_id"),
    ("payee_type_ids", "payee_type_id"),
    ("subject_ids", "kmitl_payment_subject_id"),
    ("operation_type_ids", "kmitl_payment_type_id"),
)


class PaymentReport(models.AbstractModel):
    """รายงานการจ่ายเงิน — what the treasury actually paid out, by the day it
    left.

    One row per ใบสำคัญจ่าย that has been paid, dated by **วันที่จ่ายจริง** and
    not by the day the voucher was raised: a voucher authorised on 28 September
    whose e-payment file takes effect on 2 October is October's payment, and the
    office reconciling a bank statement needs it to land there. See
    ``finance_kmitl`` ADR-0009.

    The daily and the monthly report the finance office asked for are this one
    report with two different date ranges. They differ in nothing else, and a
    second layout would have been a second place to correct a column.
    """

    _name = REPORT_MODEL
    _inherit = "finance_kmitl_reports.report.base"
    _description = "KMITL Payment Report Data Provider"

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_group_axis_titles(self):
        return {
            "paid_date": _("Actual Payment Date"),
            "payment_method_line_id": _("Paying Account"),
            "payment_method_id": _("Payment Method"),
            "source_analytic_id": _("Sources"),
            "department_analytic_id": _("Departments"),
            "kmitl_payment_subject_id": _("Payment Subject"),
            "partner_id": _("Payee"),
        }

    @api.model
    def get_group_axes(self):
        """RPC for the two group-by dropdowns: ``[{value, label}]``.

        Read off the server so the screen, the PDF header and the workbook can
        never offer an axis the grouping does not know how to fold by.
        """
        titles = self._kmitl_group_axis_titles()
        return [{"value": axis, "label": titles[axis]} for axis in GROUP_AXES]

    @api.model
    def _kmitl_dim_leaves(self, dims):
        """The dimension leaves, walked through ``move_id``.

        ``account.payment`` reaches ``analytic_distribution`` through
        ``_inherits``, and an inherited leaf is joined straight onto
        ``account.move``'s column by ``expression`` — it never passes through
        ``AnalyticMixin._search``, which is the only place a JSON leaf is
        rewritten into the ``analytic_distribution_search`` the index answers.
        Walking the relation explicitly puts the leaf back inside
        ``account.move._search``, where it works.
        """
        return [
            ("move_id.%s" % leaf[0], leaf[1], leaf[2])
            for leaf in self._kmitl_build_dim_leaves(dims)
        ]

    @api.model
    def _kmitl_domain(self, options):
        domain = [
            ("payment_type", "=", "outbound"),
            # Not `done`: an e-payment file that has been produced has not
            # necessarily been uploaded, let alone honoured. `paid` is the
            # finance office's own assertion that the payee has the money —
            # finance_kmitl ADR-0004.
            ("finance_state", "=", "paid"),
            ("company_id", "=", options.get("company_id") or self.env.company.id),
            ("paid_date", ">=", options["date_from"]),
            ("paid_date", "<=", options["date_to"]),
        ]
        domain = self._kmitl_apply_id_filters(domain, options, ID_FILTERS)
        return domain + self._kmitl_dim_leaves(options.get("dims"))

    @api.model
    def _kmitl_row(self, payment):
        # อ้างอิงการจ่าย: whichever instrument carried this one — the file
        # number for a transfer, the cheque number for a cheque, nothing at all
        # for cash, which travels in no instrument.
        reference = (
            payment.payment_export_id.name or payment.cheque_id.cheque_number or ""
        )
        paid_date = payment.paid_date
        row = {
            "id": payment.id,
            "paid_date": fields.Date.to_string(paid_date) if paid_date else "",
            "name": payment.name or "/",
            "partner": payment.partner_id.display_name or "",
            "subject": payment.kmitl_payment_subject_id.display_name or "",
            "operation_type": payment.kmitl_payment_type_id.display_name or "",
            "paying_account": payment.payment_method_line_id.display_name or "",
            "method": payment.payment_method_id.display_name or "",
            "reference": reference,
            "request": payment.disbursement_request_id.name or "",
            "amount": payment.amount,
        }
        row["_axes"] = {
            "paid_date": (row["paid_date"], row["paid_date"] or NO_VALUE),
            "payment_method_line_id": self._kmitl_axis(payment.payment_method_line_id),
            "payment_method_id": self._kmitl_axis(payment.payment_method_id),
            "source_analytic_id": self._kmitl_axis(payment.source_analytic_id),
            "department_analytic_id": self._kmitl_axis(payment.department_analytic_id),
            "kmitl_payment_subject_id": self._kmitl_axis(
                payment.kmitl_payment_subject_id
            ),
            "partner_id": self._kmitl_axis(payment.partner_id),
        }
        return row

    @api.model
    def get_report_data(self, options):
        options = options or {}
        if not options.get("date_from") or not options.get("date_to"):
            return {"groups": [], "grand_total": 0.0}

        payments = self.env["account.payment"].search(self._kmitl_domain(options))
        rows = [self._kmitl_row(payment) for payment in payments]
        # paid_date is computed from three other models, so there is no column
        # to ORDER BY — the set is one period's worth and is ordered here.
        rows.sort(key=lambda row: (row["paid_date"], row["name"]))

        group_by, group_by_2 = self._kmitl_chosen_axes(options, GROUP_AXES, "paid_date")
        return self._kmitl_group_rows(rows, group_by, group_by_2, "amount")

    # ------------------------------------------------------------------
    @api.model
    def get_columns(self):
        """The columns, once, for all three renderings.

        ``(row key, heading, is a figure, printed width)``. The screen, the PDF
        and the workbook read the same list, so a column added to one cannot go
        missing from another — which is the failure the finance office would
        notice last and trust least.
        """
        return [
            ("paid_date", _("Actual Payment Date"), False, 14),
            ("name", _("Voucher No."), False, 18),
            ("partner", _("Payee"), False, 30),
            ("subject", _("Payment Subject"), False, 24),
            ("operation_type", _("Operation Type"), False, 20),
            ("paying_account", _("Paying Account"), False, 26),
            ("method", _("Payment Method"), False, 14),
            ("reference", _("Payment Reference"), False, 18),
            ("request", _("Disbursement Request"), False, 18),
            ("amount", _("Net Amount Paid"), True, 16),
        ]

    @api.model
    def get_filter_lines(self, options):
        """What the reader restricted the report to, for the printed header."""
        options = options or {}
        lines = [
            self._kmitl_period_line(
                _("Actual Payment Date"),
                options.get("date_from"),
                options.get("date_to"),
            )
        ]
        titles = self._kmitl_group_axis_titles()
        for option_key, title, model in (
            ("paying_account_ids", _("Paying Account"), "account.payment.method.line"),
            ("method_ids", _("Payment Method"), "account.payment.method"),
            ("partner_ids", _("Payee"), "res.partner"),
            ("payee_type_ids", _("Payee Type"), "res.partner.type"),
            ("subject_ids", _("Payment Subject"), "kmitl.payment.subject"),
            ("operation_type_ids", _("Operation Type"), "kmitl.payment.type"),
        ):
            line = self._kmitl_record_filter_line(title, model, options.get(option_key))
            if line:
                lines.append(line)
        lines += self._kmitl_dim_filter_lines(options.get("dims"))

        group_by, group_by_2 = self._kmitl_chosen_axes(options, GROUP_AXES, "paid_date")
        grouping = [titles[group_by]]
        if group_by_2:
            grouping.append(titles[group_by_2])
        lines.append(_("Grouped by: %s") % " › ".join(grouping))
        return lines

    @api.model
    def get_report_note(self):
        """The one thing a reader of this report has to be told.

        A cheque is counted on the day written on it, which is the day the payee
        may present it and the day the Revenue Department treats the income as
        paid — not the day the office handed it over. The ภ.ง.ด. certificate
        already reads it that way, so saying it here keeps the two documents
        from looking like they disagree.
        """
        return _(
            "A voucher settled by cheque is counted on the date written on the "
            "cheque, not on the day the cheque was handed over — the same date "
            "the withholding-tax certificate is issued from."
        )

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_payment_pdf",
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_payment_xlsx",
        )


class PaymentReportWizard(models.TransientModel):
    _name = CARRIER_MODEL
    _description = "KMITL Payment Report Carrier"

    company_id = fields.Many2one("res.company")
    date_from = fields.Date()
    date_to = fields.Date()


class PaymentReportXlsx(models.AbstractModel):
    _name = "report.finance_kmitl_reports.payment_report_xlsx"
    _description = "KMITL Payment Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        self.env["finance_kmitl_reports.report.base"]._kmitl_write_xlsx(
            workbook,
            options,
            REPORT_MODEL,
            _("Payment Report"),
            _("Payment Report"),
            "amount",
        )


class PaymentReportPdf(models.AbstractModel):
    _name = "report.finance_kmitl_reports.payment_report_pdf"
    _description = "KMITL Payment Report PDF"

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
