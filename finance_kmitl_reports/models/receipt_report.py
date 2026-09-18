# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

from .report_base import NO_VALUE

REPORT_MODEL = "finance_kmitl_reports.receipt.report"
CARRIER_MODEL = "finance_kmitl_reports.receipt.report.wizard"

# department_analytic_id and source_analytic_id are the only two of the six
# KMITL dimensions stored on kmitl.receipt — fine to fold groups by. fund and
# activity are not stored on the receipt and must never be added here (see
# _kmitl_domain).
GROUP_AXES = (
    "date",
    "payment_type",
    "payment_method_id",
    "department_analytic_id",
    "source_analytic_id",
    "remittance_id",
    "partner_id",
)

# Control-panel picker -> the receipt field it narrows. department_ids is an
# exact match on the stored, indexed column — unlike the "Departments" dims
# chip below, it does not expand to a faculty's sub-departments.
ID_FILTERS = (
    ("method_ids", "payment_method_id"),
    ("partner_ids", "partner_id"),
    ("department_ids", "department_analytic_id"),
    ("remittance_ids", "remittance_id"),
)


class ReceiptReport(models.AbstractModel):
    """รายงานการรับเงิน — every ใบเสร็จรับเงิน whose money has reached the
    treasury, in the period it was received.

    The daily and the monthly report the finance office asked for are this one
    report with two different date ranges, the same arrangement as the
    payment report. Unlike the paying side there is only one date on a
    receipt: ``kmitl.receipt._prepare_move_vals`` books the journal entry on
    ``date``, so the receipt, this report and the ledger never disagree about
    which day the money belongs to.
    """

    _name = REPORT_MODEL
    _inherit = "finance_kmitl_reports.report.base"
    _description = "KMITL Receipt Report Data Provider"

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_group_axis_titles(self):
        return {
            "date": _("Receipt Date"),
            "payment_type": _("Payment Type"),
            "payment_method_id": _("Receiving Method"),
            "department_analytic_id": _("Departments"),
            "source_analytic_id": _("Sources"),
            "remittance_id": _("Remittance"),
            "partner_id": _("Payer"),
        }

    @api.model
    def get_group_axes(self):
        titles = self._kmitl_group_axis_titles()
        return [{"value": axis, "label": titles[axis]} for axis in GROUP_AXES]

    @api.model
    def get_columns(self):
        return [
            ("date", _("Receipt Date"), False, 14),
            ("name", _("Receipt No."), False, 18),
            ("payer", _("Payer"), False, 30),
            ("payment_type_label", _("Payment Type"), False, 14),
            ("payment_method", _("Receiving Method"), False, 20),
            ("instrument", _("Instrument"), False, 20),
            ("department", _("Issuing Department"), False, 26),
            ("remittance", _("Remittance No."), False, 18),
            ("amount_total", _("Amount"), True, 16),
        ]

    # ------------------------------------------------------------------
    @api.model
    def _kmitl_payment_type_labels(self):
        """Translated ``{value: label}`` for ``kmitl.receipt.payment_type``,
        read off the field's own selection rather than a second dict here —
        see ``receipt_kmitl_summary_report.py``'s hardcoded copy, which is
        exactly the duplication this avoids.
        """
        selection = self.env["kmitl.receipt"]._fields["payment_type"]
        return dict(selection._description_selection(self.env))

    @api.model
    def _kmitl_instrument(self, receipt):
        """The instrument that carried the money, guarded by ``payment_type``.

        ``_onchange_payment_type`` only clears ``cheque_number`` /
        ``cheque_date`` / ``transfer_date`` on the UI; a write through the API
        or an import can leave them behind on a receipt that has since become
        cash. Reading ``payment_type`` first, rather than falling back through
        whichever of the three fields happens to be set, is what keeps a cash
        row from printing a stale cheque number.
        """
        if receipt.payment_type == "cheque":
            number = receipt.cheque_number or ""
            date = (
                fields.Date.to_string(receipt.cheque_date)
                if receipt.cheque_date
                else ""
            )
            return "%s (%s)" % (number, date) if (number or date) else ""
        if receipt.payment_type == "transfer":
            return (
                fields.Date.to_string(receipt.transfer_date)
                if receipt.transfer_date
                else ""
            )
        return ""

    @api.model
    def _kmitl_domain(self, options):
        domain = [
            ("state", "=", "done"),
            ("company_id", "=", options.get("company_id") or self.env.company.id),
            ("date", ">=", options["date_from"]),
            ("date", "<=", options["date_to"]),
        ]
        domain = self._kmitl_apply_id_filters(domain, options, ID_FILTERS)
        # kmitl.receipt is an analytic.mixin in its own right (it has
        # analytic_distribution_search), so the dimension leaves apply
        # directly — no move_id detour the way account.payment needs one.
        return domain + self._kmitl_build_dim_leaves(options.get("dims"))

    @api.model
    def _kmitl_row(self, receipt, payment_type_labels):
        date = receipt.date
        payment_type_label = payment_type_labels.get(
            receipt.payment_type, receipt.payment_type or ""
        )
        row = {
            "id": receipt.id,
            "date": fields.Date.to_string(date) if date else "",
            "name": receipt.name or "/",
            "payer": receipt.customer_name or receipt.partner_id.display_name or "",
            "payment_type_label": payment_type_label,
            "payment_method": receipt.payment_method_id.display_name or "",
            "instrument": self._kmitl_instrument(receipt),
            "department": receipt.department_analytic_id.display_name or "",
            "remittance": receipt.remittance_id.name or "",
            "amount_total": receipt.amount_total,
        }
        row["_axes"] = {
            "date": (row["date"], row["date"] or NO_VALUE),
            "payment_type": (payment_type_label, payment_type_label or NO_VALUE),
            "payment_method_id": self._kmitl_axis(receipt.payment_method_id),
            "department_analytic_id": self._kmitl_axis(
                receipt.department_analytic_id
            ),
            "source_analytic_id": self._kmitl_axis(receipt.source_analytic_id),
            "remittance_id": self._kmitl_axis(receipt.remittance_id),
            "partner_id": self._kmitl_axis(receipt.partner_id),
        }
        return row

    @api.model
    def get_report_data(self, options):
        options = options or {}
        if not options.get("date_from") or not options.get("date_to"):
            return {"groups": [], "grand_total": 0.0}

        receipts = self.env["kmitl.receipt"].search(
            self._kmitl_domain(options), order="date, name"
        )
        labels = self._kmitl_payment_type_labels()
        rows = [self._kmitl_row(receipt, labels) for receipt in receipts]

        group_by, group_by_2 = self._kmitl_chosen_axes(options, GROUP_AXES, "date")
        return self._kmitl_group_rows(rows, group_by, group_by_2, "amount_total")

    # ------------------------------------------------------------------
    @api.model
    def get_filter_lines(self, options):
        options = options or {}
        lines = [
            self._kmitl_period_line(
                _("Receipt Date"), options.get("date_from"), options.get("date_to")
            )
        ]
        for option_key, title, model in (
            ("method_ids", _("Receiving Method"), "kmitl.payment.method"),
            ("partner_ids", _("Payer"), "res.partner"),
            ("department_ids", _("Issuing Department"), "account.analytic.account"),
            ("remittance_ids", _("Remittance"), "kmitl.receipt.remittance"),
        ):
            line = self._kmitl_record_filter_line(title, model, options.get(option_key))
            if line:
                lines.append(line)
        lines += self._kmitl_dim_filter_lines(options.get("dims"))

        titles = self._kmitl_group_axis_titles()
        group_by, group_by_2 = self._kmitl_chosen_axes(options, GROUP_AXES, "date")
        grouping = [titles[group_by]]
        if group_by_2:
            grouping.append(titles[group_by_2])
        lines.append(_("Grouped by: %s") % " › ".join(grouping))
        return lines

    @api.model
    def get_report_note(self):
        return _(
            "Only receipts the treasury has recorded as remitted are counted "
            "— a receipt still waiting on its remittance is money in a "
            "department's drawer, not yet the treasury's."
        )

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_receipt_pdf",
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            CARRIER_MODEL,
            "finance_kmitl_reports.action_report_receipt_xlsx",
        )


class ReceiptReportWizard(models.TransientModel):
    _name = CARRIER_MODEL
    _description = "KMITL Receipt Report Carrier"

    company_id = fields.Many2one("res.company")
    date_from = fields.Date()
    date_to = fields.Date()


class ReceiptReportXlsx(models.AbstractModel):
    _name = "report.finance_kmitl_reports.receipt_report_xlsx"
    _description = "KMITL Receipt Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        self.env["finance_kmitl_reports.report.base"]._kmitl_write_xlsx(
            workbook,
            options,
            REPORT_MODEL,
            _("Receipt Report"),
            _("Receipt Report"),
            "amount_total",
        )


class ReceiptReportPdf(models.AbstractModel):
    _name = "report.finance_kmitl_reports.receipt_report_pdf"
    _description = "KMITL Receipt Report PDF"

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
