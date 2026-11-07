import pytz

from odoo import api, fields, models
from odoo.osv import expression

REPORT_MODEL = "advance.payment.overview.report"
CARRIER_MODEL = "advance.payment.overview.report.wizard"
BANGKOK_TZ = pytz.timezone("Asia/Bangkok")
NO_VALUE = "—"
BLANK_KEY = "~"

# Not yet asked for (draft) or never going to be (cancel).
EXCLUDED_STATES = ("draft", "cancel")
TOTAL_KEYS = ("loan_amount", "cleared_amount", "remaining_amount")
# Group-by levels the report folds into; the search model may hold more.
MAX_GROUP_LEVELS = 2


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    # Search-only: one box for every number around the loan. The linked
    # documents are matched under sudo, since the loan officer need not read
    # budget, disbursement or accounting records.
    overview_document_number = fields.Char(
        string="เลขที่เอกสาร",
        compute="_compute_overview_document_number",
        search="_search_overview_document_number",
    )

    def _compute_overview_document_number(self):
        self.overview_document_number = False

    def _search_overview_document_number(self, operator, value):
        negative = operator in expression.NEGATIVE_TERM_OPERATORS
        if negative:
            operator = expression.TERM_OPERATORS_NEGATION[operator]
        if operator not in ("ilike", "=", "like") or not value:
            return []
        loans = self.sudo().search(
            [
                "|",
                "|",
                "|",
                "|",
                "|",
                "|",
                ("name", operator, value),
                ("contract_number", operator, value),
                ("reference_number", operator, value),
                ("budget_commitment_id.name", operator, value),
                ("disbursement_request_ids.name", operator, value),
                ("payment_ids.name", operator, value),
                ("employee_id.name", operator, value),
            ]
        )
        return [("id", "not in" if negative else "in", loans.ids)]


class AdvancePaymentOverviewReport(models.AbstractModel):
    """รายงานภาพรวมสัญญายืมเงิน — one row per submitted agreement with every
    document number around it, so the loan officer need not open each form.

    The screen's search model (domain, group-by, facets) drives the rows. The
    loans are searched with the user's own rights (OU rules apply); the linked
    BC/DR/voucher numbers and the ส่วนงาน name are read under sudo.
    """

    _name = REPORT_MODEL
    _description = "Advance Payment Overview Report Data Provider"

    @api.model
    def get_search_view_id(self):
        return self.env.ref("advance_payment_overview_report.view_overview_search").id

    @api.model
    def get_columns(self):
        """``(row key, heading, is a figure, printed width)`` for the screen,
        the PDF and the workbook alike — kept to what debt follow-up needs."""
        return [
            ("contract", "เลขที่สัญญา", False, 18),
            ("employee", "ผู้ยืม", False, 24),
            ("department", "ส่วนงาน", False, 26),
            ("state", "สถานะ", False, 14),
            ("effective_date", "วันที่เป็นลูกหนี้", False, 14),
            ("documents", "เอกสารอ้างอิง", False, 24),
            ("loan_amount", "จำนวนเงินยืม", True, 15),
            ("cleared_amount", "ส่งใช้คืน", True, 15),
            ("remaining_amount", "คงเหลือ", True, 15),
            ("return_due_date", "วันที่ครบกำหนด", False, 14),
            ("return_due_status", "สถานะวันครบกำหนด", False, 18),
        ]

    # ------------------------------------------------------------------
    # Rows
    # ------------------------------------------------------------------
    @api.model
    def _selection_labels(self, field_name):
        field = self.env["advance.payment"]._fields[field_name]
        return dict(field._description_selection(self.env))

    @api.model
    def _local_date(self, value):
        """Datetime -> the Bangkok calendar day it fell on."""
        if not value:
            return False
        return value.replace(tzinfo=pytz.utc).astimezone(BANGKOK_TZ).date()

    @api.model
    def _documents(self, loan, readable):
        """The documents around the loan, in order: its source, its
        commitment (once, when the source is the commitment itself) and every
        live ใบเบิกชดใช้เงินยืม. ``link`` only where the user may read that
        model at all (record rules may still refuse a single record)."""
        commitment = loan.budget_commitment_id
        records = []
        if loan.reference and loan.reference != commitment:
            records.append(loan.reference)
        if commitment:
            records.append(commitment)
        records += loan.disbursement_request_ids.filtered(
            lambda r: r.state != "cancel"
        ).sorted("name")
        documents = []
        for record in records:
            if record._name not in readable:
                readable[record._name] = self.env[record._name].check_access_rights(
                    "read", raise_exception=False
                )
            if record == loan.reference:
                name = loan.reference_number or record.display_name
            else:
                name = record.name
            documents.append(
                {
                    "name": name,
                    "model": record._name,
                    "id": record.id,
                    "link": readable[record._name],
                }
            )
        return documents

    @api.model
    def _due_text(self, loan, due_statuses):
        """The due status with its day count, e.g. "เกินกำหนด 5 วัน"."""
        status = loan.return_due_status
        if status == "overdue":
            return "%s %d วัน" % (due_statuses[status], -loan.days_to_return)
        if status == "not_due":
            return "%s (อีก %d วัน)" % (due_statuses[status], loan.days_to_return)
        return due_statuses.get(status, "")

    @api.model
    def _row(self, loan, states, due_statuses, readable):
        thai = self.env["thai.date.mixin"]
        sudo_loan = loan.sudo()
        # The contract number once there is one, the ADV number beneath it.
        numbers = [n for n in (loan.contract_number, loan.name) if n]
        documents = self._documents(sudo_loan, readable)
        return {
            "id": loan.id,
            "contract": "\n".join(numbers),
            "employee": sudo_loan.employee_id.name or "",
            "department": sudo_loan.department_analytic_id.display_name or "",
            "state": states.get(loan.state, ""),
            "state_code": loan.state,
            "effective_date": thai.format_date_thai_short(loan.effective_date),
            # Text for the PDF and the workbook; links for the screen.
            "documents": "\n".join(d["name"] for d in documents),
            "document_links": documents,
            "return_due_date": thai.format_date_thai_short(loan.return_due_date),
            "return_due_status": self._due_text(loan, due_statuses),
            "return_due_status_code": loan.return_due_status or "",
            "loan_amount": loan.loan_amount,
            "cleared_amount": loan.actual_expense_amount,
            "remaining_amount": loan.amount_remaining,
        }

    # ------------------------------------------------------------------
    # Grouping — by whatever the search model's Group By holds
    # ------------------------------------------------------------------
    @api.model
    def _group_specs(self, group_by):
        """The first levels of ``group_by`` that name a real loan field."""
        fields_map = self.env["advance.payment"]._fields
        specs = []
        for spec in group_by or []:
            if spec.split(":")[0] in fields_map and spec not in specs:
                specs.append(spec)
        return specs[:MAX_GROUP_LEVELS]

    @api.model
    def _axis(self, loan, spec):
        """``(sort key, label)`` of ``loan`` on a group-by spec; blank last."""
        field_name, _sep, interval = spec.partition(":")
        field = loan._fields[field_name]
        value = loan.sudo()[field_name]
        if not value:
            return (BLANK_KEY, NO_VALUE)
        if field.type == "many2one":
            # The id keeps same-named records (two namesake borrowers) apart.
            label = value.display_name or ""
            return ("%s\x00%d" % (label, value.id), label)
        if field.type == "selection":
            choices = field._description_selection(self.env)
            keys = [key for key, _label in choices]
            return ("%03d" % keys.index(value), dict(choices).get(value, value))
        if field.type in ("date", "datetime"):
            day = self._local_date(value) if field.type == "datetime" else value
            thai = self.env["thai.date.mixin"]
            if interval == "day":
                return (str(day), thai.format_date_thai_short(day))
            if interval == "year":
                return (str(day.year), str(day.year + 543))
            if interval == "quarter":
                quarter = (day.month - 1) // 3 + 1
                return (
                    "%d-Q%d" % (day.year, quarter),
                    "ไตรมาส %d %d" % (quarter, day.year + 543),
                )
            if interval == "week":
                year, week, _weekday = day.isocalendar()
                return ("%d-W%02d" % (year, week), "สัปดาห์ %d %d" % (week, year + 543))
            # month — Odoo's default interval — for anything else
            label = thai.format_date_thai_short(day).split(" ", 1)[1]
            return (day.strftime("%Y-%m"), label)
        return (str(value), str(value))

    @api.model
    def _empty_totals(self):
        return dict.fromkeys(TOTAL_KEYS, 0.0)

    @api.model
    def _add_totals(self, totals, row):
        for key in TOTAL_KEYS:
            totals[key] += row.get(key) or 0.0

    @api.model
    def _group_rows(self, loans, specs):
        """Fold the rows into up to two levels of groups, each totalling every
        figure column. With no group-by, one unnamed group holds every row."""
        states = self._selection_labels("state")
        due_statuses = self._selection_labels("return_due_status")
        readable = {}
        top = {}
        grand = self._empty_totals()
        for loan in loans:
            row = self._row(loan, states, due_statuses, readable)
            self._add_totals(grand, row)
            key_1, label_1 = self._axis(loan, specs[0]) if specs else ("", "")
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
            if len(specs) > 1:
                key_2, label_2 = self._axis(loan, specs[1])
                sub = group["subs"].setdefault(
                    key_2,
                    {
                        "key": key_2,
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

        def blank_last(key):
            return (key == BLANK_KEY, key)

        groups = []
        for key in sorted(top, key=blank_last):
            group = top[key]
            subs = group.pop("subs")
            group["subgroups"] = [subs[k] for k in sorted(subs, key=blank_last)]
            groups.append(group)
        return {
            "groups": groups,
            "totals": grand,
            "grouped": bool(specs),
            "count": len(loans),
        }

    @api.model
    def get_report_data(self, options):
        """``options``: the search model's ``domain`` and ``group_by``."""
        options = options or {}
        domain = expression.AND(
            [[("state", "not in", EXCLUDED_STATES)], options.get("domain") or []]
        )
        loans = self.env["advance.payment"].search(domain, order="date_submitted, id")
        return self._group_rows(loans, self._group_specs(options.get("group_by")))

    # ------------------------------------------------------------------
    # Print / export
    # ------------------------------------------------------------------
    @api.model
    def get_filter_lines(self, options):
        """The search facets as the reader saw them, for the printed header."""
        return [line for line in (options or {}).get("facets") or [] if line]

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
        carrier = self.env[CARRIER_MODEL].create({"company_id": self.env.company.id})
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options or {}})

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
        sheet.merge_range(0, 0, 0, last_col, self.env.company.display_name, bold)
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
            "company": self.env.company,
            "columns": columns,
            "label_span": [column[2] for column in columns].index(True),
            "groups": result["groups"],
            "grouped": result["grouped"],
            "totals": result["totals"],
            "filter_lines": report.get_filter_lines(options),
            "format_amount": report.format_amount,
        }
