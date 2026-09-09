# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models

# The dimension chips the two report screens offer, in display order. The same
# four the mixin filters on — kmitl_project and procurement_plan are not among
# them because neither the finance office's payment register nor the payables
# ledger is worked by project.
DIM_CODES = ("departments", "sources", "funds", "activities")

# What a group header says when the records in it have nothing on the axis.
NO_VALUE = "—"


class FinanceReportBase(models.AbstractModel):
    """What the two รายงานฝั่งรายจ่าย have in common.

    Both are a flat list of documents that the officer folds up on screen — up
    to two levels, chosen from a dropdown rather than fixed by the report — and
    both are then printed and exported from exactly the data the screen showed.
    So the grouping is written once, here, and each report only says what its
    rows are and which axes it can be folded by.
    """

    _name = "finance_kmitl_reports.report.base"
    _inherit = "accounting_kmitl_reports.dimension.filter.mixin"
    _description = "KMITL Finance Report Base"

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_group_rows(self, rows, axis_1, axis_2, amount_key):
        """Fold ``rows`` into one or two levels of totalled groups.

        Every row carries its axis values under ``_axes``: ``{axis: [sort,
        label]}``. Keeping them on the row rather than re-reading the record
        means the totals, the screen, the PDF and the workbook are all folded
        by the same values — the alternative is four places that each decide
        for themselves what "grouped by ผู้รับเงิน" means.

        The second level is optional. When there is none the rows hang straight
        off the top-level group, rather than off a single unnamed subgroup: a
        header row that names nothing is a row the reader has to skip.
        """
        axis_1 = axis_1 or None
        axis_2 = axis_2 or None
        if axis_2 == axis_1:
            axis_2 = None

        top = {}
        for row in rows:
            axes = row.pop("_axes", {})
            key_1, label_1 = axes.get(axis_1) or ("", NO_VALUE)
            group = top.setdefault(
                key_1,
                {"key": key_1, "label": label_1, "total": 0.0, "rows": [], "subs": {}},
            )
            amount = row.get(amount_key) or 0.0
            group["total"] += amount
            if axis_2:
                key_2, label_2 = axes.get(axis_2) or ("", NO_VALUE)
                sub = group["subs"].setdefault(
                    key_2,
                    {"key": key_2, "label": label_2, "total": 0.0, "rows": []},
                )
                sub["total"] += amount
                sub["rows"].append(row)
            else:
                group["rows"].append(row)

        groups = []
        for key in sorted(top):
            group = top[key]
            subs = group.pop("subs")
            group["subgroups"] = [subs[sub_key] for sub_key in sorted(subs)]
            groups.append(group)

        return {
            "groups": groups,
            "grand_total": sum(group["total"] for group in groups),
        }

    @api.model
    def _kmitl_chosen_axes(self, options, allowed, default):
        """The two axes to fold by, validated.

        ``get_report_data`` is a public RPC and the dropdowns are built from
        another one, so a screen left open across an upgrade can ask for an axis
        that no longer exists. Validating in one place keeps the data and the
        printed "Grouped by" line from ever disagreeing about what was asked
        for.
        """
        group_by = options.get("group_by")
        if group_by not in allowed:
            group_by = default
        group_by_2 = options.get("group_by_2")
        if group_by_2 not in allowed or group_by_2 == group_by:
            group_by_2 = None
        return group_by, group_by_2

    @api.model
    def _kmitl_axis(self, record_field):
        """``(sort, label)`` for a Many2one axis value, blank ones last.

        The empty key sorts before every real name, which puts the unnamed
        group at the top; the label says so out loud instead of leaving a blank
        header the reader has to guess at.
        """
        if not record_field:
            return ("", NO_VALUE)
        name = record_field.display_name or ""
        return (name, name)

    # ------------------------------------------------------------------
    # Filter descriptions, for the PDF header
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_dim_titles(self):
        """Translated dimension headings, keyed by plan code."""
        return {
            "departments": _("Departments"),
            "sources": _("Sources"),
            "funds": _("Funds"),
            "activities": _("Activities"),
        }

    @api.model
    def _kmitl_dim_filter_lines(self, dims):
        """One line per dimension the reader restricted the report to."""
        lines = []
        titles = self._kmitl_dim_titles()
        analytic = self.env["account.analytic.account"]
        for code in DIM_CODES:
            ids = (dims or {}).get(code) or []
            if ids:
                names = analytic.browse(ids).exists().mapped("display_name")
                lines.append("%s: %s" % (titles[code], ", ".join(names)))
        return lines

    @api.model
    def _kmitl_record_filter_line(self, title, model, ids):
        if not ids:
            return None
        names = self.env[model].browse(ids).exists().mapped("display_name")
        if not names:
            return None
        return "%s: %s" % (title, ", ".join(names))

    @api.model
    def _kmitl_period_line(self, title, date_from, date_to):
        return _("%(title)s: %(date_from)s – %(date_to)s") % {
            "title": title,
            "date_from": date_from or "",
            "date_to": date_to or "",
        }

    # ------------------------------------------------------------------
    # Shared formatting
    # ------------------------------------------------------------------
    @api.model
    def format_amount(self, value):
        """Blank rather than 0.00 for nothing, so the eye finds the figures."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    @api.model
    def _kmitl_apply_id_filters(self, domain, options, mapping):
        """Append one ``in`` leaf per filled-in picker on the control panel."""
        for option_key, field_name in mapping:
            ids = options.get(option_key) or []
            if ids:
                domain.append((field_name, "in", ids))
        return domain

    # ------------------------------------------------------------------
    # Print / export plumbing
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_report_action(self, options, carrier_model, report_xmlid):
        """Hand the on-screen options to a printable action.

        ``ir.actions.report`` needs a record to print, and there is none: the
        report is a query, not a document. So a throwaway carrier is created to
        be that record and the options travel beside it in ``data``, which is
        the same arrangement every other KMITL OWL report uses.
        """
        options = options or {}
        carrier = self.env[carrier_model].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options})

    @api.model
    def _kmitl_write_xlsx(
        self, workbook, options, report_model, sheet_name, title, total_key
    ):
        """The workbook every KMITL finance report writes: a title band, the
        filter lines, one header row, groups of totalled bands, and a grand
        total — read from the same ``get_report_data`` the screen and the PDF
        call. Written once here rather than once per report so a column added
        to a report cannot go missing from its workbook.
        """
        report = self.env[report_model]
        result = report.get_report_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        columns = report.get_columns()

        sheet = workbook.add_worksheet(sheet_name)
        bold = workbook.add_format({"bold": True})
        head = workbook.add_format(
            {"bold": True, "bg_color": "#F0F0F0", "border": 1, "align": "center"}
        )
        group = workbook.add_format({"bold": True, "bg_color": "#EDEDED"})
        group_num = workbook.add_format(
            {"bold": True, "bg_color": "#EDEDED", "num_format": "#,##0.00"}
        )
        sub = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        sub_num = workbook.add_format(
            {"bold": True, "bg_color": "#F7F7F7", "num_format": "#,##0.00"}
        )
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        total_fmt = workbook.add_format({"bold": True, "num_format": "#,##0.00"})

        last_col = len(columns) - 1
        total_col = [key for key, _h, _a, _w in columns].index(total_key)

        sheet.merge_range(0, 0, 0, last_col, company.display_name, bold)
        sheet.merge_range(1, 0, 1, last_col, title, bold)
        row_index = 2
        for line in report.get_filter_lines(options):
            sheet.merge_range(row_index, 0, row_index, last_col, line)
            row_index += 1
        sheet.merge_range(row_index, 0, row_index, last_col, report.get_report_note())
        row_index += 2

        for col, (_key, heading, _is_amount, _width) in enumerate(columns):
            sheet.write(row_index, col, heading, head)
        row_index += 1

        def write_band(index, label, total, label_fmt, total_format):
            for col in range(len(columns)):
                sheet.write(index, col, "", label_fmt)
            sheet.write(index, 0, label, label_fmt)
            sheet.write_number(index, total_col, total, total_format)
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

        for group_data in result.get("groups", []):
            row_index = write_band(
                row_index, group_data["label"], group_data["total"], group, group_num
            )
            row_index = write_rows(row_index, group_data.get("rows", []))
            for sub_data in group_data.get("subgroups", []):
                row_index = write_band(
                    row_index, sub_data["label"], sub_data["total"], sub, sub_num
                )
                row_index = write_rows(row_index, sub_data.get("rows", []))

        row_index += 1
        sheet.write(row_index, 0, _("Grand Total"), bold)
        sheet.write_number(
            row_index, total_col, result.get("grand_total", 0), total_fmt
        )

        for col, (_key, _heading, _is_amount, width) in enumerate(columns):
            sheet.set_column(col, col, width)
