from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.tools import date_utils

REPORT_MODEL = "advance.payment.overview.report"
CARRIER_MODEL = "advance.payment.overview.report.wizard"
BANGKOK_TZ = pytz.timezone("Asia/Bangkok")
NO_VALUE = "—"

# Not yet asked for (draft) or never going to be (cancel).
EXCLUDED_STATES = ("draft", "cancel")
TOTAL_KEYS = ("loan_amount", "cleared_amount", "remaining_amount")
GROUP_AXES = ("operating_unit_id", "state", "loan_type_id", "return_due_status")

# Control-panel picker -> the loan field it narrows.
ID_FILTERS = (
    ("operating_unit_ids", "operating_unit_id"),
    ("employee_ids", "employee_id"),
    ("loan_type_ids", "loan_type_id"),
)


class AdvancePaymentOverviewReport(models.AbstractModel):
    """รายงานภาพรวมสัญญายืมเงิน — one row per submitted agreement with every
    document number around it, so the loan officer need not open each form.

    The rows are searched with the user's own rights (OU rules apply); the
    linked BC/DR/voucher numbers are read under sudo, since the officer need
    not hold budget, disbursement or accounting rights.
    """

    _name = REPORT_MODEL
    _description = "Advance Payment Overview Report Data Provider"

    # ------------------------------------------------------------------
    # Metadata RPCs
    # ------------------------------------------------------------------
    @api.model
    def get_columns(self):
        """``(row key, heading, is a figure, printed width)`` for the screen,
        the PDF and the workbook alike."""
        return [
            ("name", "เลขที่คำขอ", False, 16),
            ("contract_number", "เลขที่สัญญา", False, 16),
            ("employee", "ผู้ยืม", False, 26),
            ("operating_unit", "ส่วนงาน", False, 22),
            ("loan_type", "ประเภทเงินยืม", False, 22),
            ("state", "สถานะ", False, 18),
            ("date_submitted", "วันที่ส่งคำขอ", False, 14),
            ("reference_number", "เอกสารต้นเรื่อง (AR/PR)", False, 18),
            ("budget_commitment", "ใบจองงบ (BC)", False, 18),
            ("payments", "ใบสำคัญจ่าย", False, 18),
            ("effective_date", "วันที่เป็นลูกหนี้", False, 14),
            ("return_due_date", "วันที่ครบกำหนด", False, 14),
            ("return_due_status", "สถานะวันครบกำหนด", False, 16),
            ("loan_amount", "จำนวนเงินยืม", True, 16),
            ("cleared_amount", "ส่งใช้คืน", True, 16),
            ("remaining_amount", "คงเหลือ", True, 16),
            ("disbursement_requests", "ใบเบิกชดใช้เงินยืม (DR)", False, 20),
        ]

    @api.model
    def _group_axis_titles(self):
        return {
            "operating_unit_id": "ส่วนงาน",
            "state": "สถานะ",
            "loan_type_id": "ประเภทเงินยืม",
            "return_due_status": "สถานะวันครบกำหนด",
        }

    @api.model
    def get_group_axes(self):
        titles = self._group_axis_titles()
        return [{"value": axis, "label": titles[axis]} for axis in GROUP_AXES]

    @api.model
    def _selection(self, field_name):
        field = self.env["advance.payment"]._fields[field_name]
        return field._description_selection(self.env)

    @api.model
    def get_selections(self):
        """State and due-status choices for the two plain dropdown filters."""
        states = [
            {"value": value, "label": label}
            for value, label in self._selection("state")
            if value not in EXCLUDED_STATES
        ]
        due = [
            {"value": value, "label": label}
            for value, label in self._selection("return_due_status")
        ]
        return {"states": states, "return_due_statuses": due}

    @api.model
    def get_default_options(self):
        """The current fiscal year (1 ต.ค. – 30 ก.ย.), by วันที่ส่งคำขอ."""
        company = self.env.company
        today = fields.Date.context_today(self)
        fiscal_year = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", company.id),
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ],
            limit=1,
        )
        if fiscal_year:
            date_from, date_to = fiscal_year.date_from, fiscal_year.date_to
        else:
            date_from, date_to = date_utils.get_fiscal_year(
                today,
                day=company.fiscalyear_last_day,
                month=int(company.fiscalyear_last_month),
            )
        return {
            "date_from": fields.Date.to_string(date_from),
            "date_to": fields.Date.to_string(date_to),
        }

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    @api.model
    def _utc_bound(self, date_value, next_day=False):
        """Bangkok midnight of ``date_value`` (or of the next day) in naive UTC,
        so a request sent at 03:00 on 1 ต.ค. lands in the new fiscal year."""
        day = fields.Date.to_date(date_value)
        if next_day:
            day += timedelta(days=1)
        local = BANGKOK_TZ.localize(datetime.combine(day, time.min))
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _text_domain(self, text):
        """Any document number: the loan's own ones directly, the linked ones
        resolved under sudo (the officer may not read those models)."""
        linked = (
            self.env["advance.payment"]
            .sudo()
            .search(
                [
                    "|",
                    "|",
                    ("budget_commitment_id.name", "ilike", text),
                    ("disbursement_request_ids.name", "ilike", text),
                    ("payment_ids.name", "ilike", text),
                ]
            )
        )
        return [
            "|",
            "|",
            "|",
            "|",
            ("name", "ilike", text),
            ("contract_number", "ilike", text),
            ("reference_number", "ilike", text),
            ("employee_id.name", "ilike", text),
            ("id", "in", linked.ids),
        ]

    @api.model
    def _domain(self, options):
        domain = [("state", "not in", EXCLUDED_STATES)]
        if options.get("date_from"):
            domain.append(
                ("date_submitted", ">=", self._utc_bound(options["date_from"]))
            )
        if options.get("date_to"):
            domain.append(
                (
                    "date_submitted",
                    "<",
                    self._utc_bound(options["date_to"], next_day=True),
                )
            )
        if options.get("states"):
            domain.append(("state", "in", options["states"]))
        if options.get("return_due_statuses"):
            domain.append(("return_due_status", "in", options["return_due_statuses"]))
        for option_key, field_name in ID_FILTERS:
            if options.get(option_key):
                domain.append((field_name, "in", options[option_key]))
        text = (options.get("search") or "").strip()
        if text:
            domain += self._text_domain(text)
        return domain

    @api.model
    def _axis(self, record):
        if not record:
            return ("", NO_VALUE)
        name = record.display_name or ""
        return (name, name)

    @api.model
    def _row(self, loan, state_labels, due_labels):
        thai = self.env["thai.date.mixin"]
        sudo_loan = loan.sudo()
        payments = sudo_loan.payment_ids.filtered(
            lambda p: p.state != "cancel"
        ).sorted("name")
        requests = sudo_loan.disbursement_request_ids.filtered(
            lambda r: r.state != "cancel"
        ).sorted("name")
        state_label = state_labels.get(loan.state, "")
        due_label = due_labels.get(loan.return_due_status, "")
        # Datetime -> the Bangkok calendar day it was sent on.
        submitted = (
            loan.date_submitted.replace(tzinfo=pytz.utc).astimezone(BANGKOK_TZ).date()
            if loan.date_submitted
            else False
        )
        row = {
            "id": loan.id,
            "name": loan.name or "",
            "contract_number": loan.contract_number or "",
            "employee": loan.employee_id.name or "",
            "operating_unit": loan.operating_unit_id.display_name or "",
            "loan_type": loan.loan_type_id.display_name or "",
            "state": state_label,
            "state_code": loan.state,
            "date_submitted": thai.format_date_thai_short(submitted),
            "reference_number": loan.reference_number or "",
            "budget_commitment": sudo_loan.budget_commitment_id.name or "",
            "payments": "\n".join(p.name for p in payments if p.name),
            "effective_date": thai.format_date_thai_short(loan.effective_date),
            "return_due_date": thai.format_date_thai_short(loan.return_due_date),
            "return_due_status": due_label,
            "return_due_status_code": loan.return_due_status or "",
            "loan_amount": loan.loan_amount,
            "cleared_amount": loan.actual_expense_amount,
            "remaining_amount": loan.amount_remaining,
            "disbursement_requests": "\n".join(r.name for r in requests if r.name),
        }
        row["_axes"] = {
            "operating_unit_id": self._axis(loan.operating_unit_id),
            # Sort states by workflow order, not alphabetically.
            "state": (
                "%02d" % list(state_labels).index(loan.state),
                state_label,
            ),
            "loan_type_id": self._axis(loan.loan_type_id),
            "return_due_status": (
                loan.return_due_status or "",
                due_label or NO_VALUE,
            ),
        }
        return row

    @api.model
    def _chosen_axes(self, options):
        group_by = options.get("group_by")
        if group_by not in GROUP_AXES:
            group_by = None
        group_by_2 = options.get("group_by_2")
        if not group_by or group_by_2 not in GROUP_AXES or group_by_2 == group_by:
            group_by_2 = None
        return group_by, group_by_2

    @api.model
    def _empty_totals(self):
        return dict.fromkeys(TOTAL_KEYS, 0.0)

    @api.model
    def _add_totals(self, totals, row):
        for key in TOTAL_KEYS:
            totals[key] += row.get(key) or 0.0

    @api.model
    def _group_rows(self, rows, axis_1, axis_2):
        """Fold rows into up to two levels of groups, each totalling every
        figure column. With no axis, one unnamed group holds every row."""
        top = {}
        grand = self._empty_totals()
        for row in rows:
            axes = row.pop("_axes", {})
            self._add_totals(grand, row)
            key_1, label_1 = axes[axis_1] if axis_1 else ("", "")
            group = top.setdefault(
                key_1,
                {
                    "key": key_1 or "all",
                    "label": label_1,
                    "count": 0,
                    "totals": self._empty_totals(),
                    "rows": [],
                    "subs": {},
                },
            )
            self._add_totals(group["totals"], row)
            group["count"] += 1
            if axis_2:
                key_2, label_2 = axes.get(axis_2) or ("", NO_VALUE)
                sub = group["subs"].setdefault(
                    key_2,
                    {
                        "key": key_2 or "none",
                        "label": label_2,
                        "count": 0,
                        "totals": self._empty_totals(),
                        "rows": [],
                    },
                )
                self._add_totals(sub["totals"], row)
                sub["count"] += 1
                sub["rows"].append(row)
            else:
                group["rows"].append(row)

        groups = []
        for key in sorted(top):
            group = top[key]
            subs = group.pop("subs")
            group["subgroups"] = [subs[sub_key] for sub_key in sorted(subs)]
            groups.append(group)
        return {"groups": groups, "totals": grand, "grouped": bool(axis_1)}

    @api.model
    def get_report_data(self, options):
        options = options or {}
        loans = self.env["advance.payment"].search(
            self._domain(options), order="date_submitted, id"
        )
        state_labels = dict(self._selection("state"))
        due_labels = dict(self._selection("return_due_status"))
        rows = [self._row(loan, state_labels, due_labels) for loan in loans]
        group_by, group_by_2 = self._chosen_axes(options)
        return self._group_rows(rows, group_by, group_by_2)

    # ------------------------------------------------------------------
    # Print / export
    # ------------------------------------------------------------------
    @api.model
    def get_filter_lines(self, options):
        """What the reader restricted the report to, for the printed header."""
        options = options or {}
        thai = self.env["thai.date.mixin"]
        lines = [
            "วันที่ส่งคำขอ: %s – %s"
            % (
                thai.format_date_thai_short(options.get("date_from")) or "…",
                thai.format_date_thai_short(options.get("date_to")) or "…",
            )
        ]
        selections = self.get_selections()
        for key, title, choices in (
            ("states", "สถานะ", selections["states"]),
            (
                "return_due_statuses",
                "สถานะวันครบกำหนด",
                selections["return_due_statuses"],
            ),
        ):
            chosen = options.get(key) or []
            if chosen:
                labels = [c["label"] for c in choices if c["value"] in chosen]
                lines.append("%s: %s" % (title, ", ".join(labels)))
        for option_key, title, model in (
            ("operating_unit_ids", "ส่วนงาน", "operating.unit"),
            ("employee_ids", "ผู้ยืม", "hr.employee"),
            ("loan_type_ids", "ประเภทเงินยืม", "advance.payment.loan.type"),
        ):
            ids = options.get(option_key) or []
            if ids:
                names = self.env[model].browse(ids).exists().mapped("display_name")
                lines.append("%s: %s" % (title, ", ".join(names)))
        if (options.get("search") or "").strip():
            lines.append("ค้นหา: %s" % options["search"].strip())
        group_by, group_by_2 = self._chosen_axes(options)
        if group_by:
            titles = self._group_axis_titles()
            grouping = [titles[group_by]] + ([titles[group_by_2]] if group_by_2 else [])
            lines.append("จัดกลุ่มตาม: %s" % " › ".join(grouping))
        return lines

    @api.model
    def format_amount(self, value):
        """Blank rather than 0.00 for nothing, so the eye finds the figures."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    @api.model
    def _report_action(self, options, report_xmlid):
        """ir.actions.report needs a record: a throwaway carrier stands in, and
        the on-screen options travel beside it in ``data``."""
        options = options or {}
        carrier = self.env[CARRIER_MODEL].create(
            {"company_id": options.get("company_id") or self.env.company.id}
        )
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options})

    @api.model
    def action_print_pdf(self, options):
        return self._report_action(
            options, "advance_payment_overview_report.action_report_overview_pdf"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._report_action(
            options, "advance_payment_overview_report.action_report_overview_xlsx"
        )


class AdvancePaymentOverviewReportWizard(models.TransientModel):
    _name = CARRIER_MODEL
    _description = "Advance Payment Overview Report Carrier"

    company_id = fields.Many2one("res.company")


class AdvancePaymentOverviewReportXlsx(models.AbstractModel):
    _name = "report.advance_payment_overview_report.overview_xlsx"
    _description = "Advance Payment Overview Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        report = self.env[REPORT_MODEL]
        result = report.get_report_data(options)
        columns = report.get_columns()
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet("ภาพรวมสัญญายืมเงิน")
        bold = workbook.add_format({"bold": True})
        head = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#F0F0F0",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        )
        group_fmt = workbook.add_format({"bold": True, "bg_color": "#EDEDED"})
        group_num = workbook.add_format(
            {"bold": True, "bg_color": "#EDEDED", "num_format": "#,##0.00"}
        )
        sub_fmt = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        sub_num = workbook.add_format(
            {"bold": True, "bg_color": "#F7F7F7", "num_format": "#,##0.00"}
        )
        cell = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})
        num = workbook.add_format(
            {"border": 1, "valign": "top", "num_format": "#,##0.00"}
        )
        total_fmt = workbook.add_format(
            {"bold": True, "top": 1, "bottom": 6, "num_format": "#,##0.00"}
        )

        last_col = len(columns) - 1
        sheet.merge_range(0, 0, 0, last_col, company.display_name, bold)
        sheet.merge_range(1, 0, 1, last_col, "รายงานภาพรวมสัญญายืมเงิน", bold)
        row_index = 2
        for line in report.get_filter_lines(options):
            sheet.merge_range(row_index, 0, row_index, last_col, line)
            row_index += 1
        row_index += 1

        for col, (_key, heading, _is_amount, width) in enumerate(columns):
            sheet.write(row_index, col, heading, head)
            sheet.set_column(col, col, width)
        sheet.freeze_panes(row_index + 1, 2)
        row_index += 1

        def write_band(index, label, totals, label_fmt, total_format):
            for col, (key, _h, is_amount, _w) in enumerate(columns):
                if is_amount:
                    sheet.write_number(index, col, totals.get(key, 0.0), total_format)
                else:
                    sheet.write(index, col, label if col == 0 else "", label_fmt)
            return index + 1

        def write_rows(index, rows):
            for row in rows:
                for col, (key, _heading, is_amount, _width) in enumerate(columns):
                    if is_amount:
                        amount = row.get(key) or 0.0
                        if abs(amount) >= 0.005:
                            sheet.write_number(index, col, amount, num)
                        else:
                            sheet.write_blank(index, col, None, num)
                    else:
                        sheet.write(index, col, row.get(key) or "", cell)
                index += 1
            return index

        for group in result["groups"]:
            if result["grouped"]:
                row_index = write_band(
                    row_index, group["label"], group["totals"], group_fmt, group_num
                )
            row_index = write_rows(row_index, group["rows"])
            for sub in group["subgroups"]:
                row_index = write_band(
                    row_index, sub["label"], sub["totals"], sub_fmt, sub_num
                )
                row_index = write_rows(row_index, sub["rows"])

        write_band(row_index, "รวมทั้งสิ้น", result["totals"], bold, total_fmt)


class AdvancePaymentOverviewReportPdf(models.AbstractModel):
    _name = "report.advance_payment_overview_report.overview_pdf"
    _description = "Advance Payment Overview Report PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        options = (data or {}).get("options") or {}
        report = self.env[REPORT_MODEL]
        result = report.get_report_data(options)
        columns = report.get_columns()
        return {
            "doc_ids": docids,
            "doc_model": CARRIER_MODEL,
            "docs": self.env[CARRIER_MODEL].browse(docids),
            "company": self.env["res.company"].browse(
                options.get("company_id") or self.env.company.id
            ),
            "columns": columns,
            "label_span": [column[2] for column in columns].index(True),
            "groups": result["groups"],
            "grouped": result["grouped"],
            "totals": result["totals"],
            "filter_lines": report.get_filter_lines(options),
            "format_amount": report.format_amount,
        }
