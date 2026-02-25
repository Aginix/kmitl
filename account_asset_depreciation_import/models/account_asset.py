# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountAsset(models.Model):
    _inherit = "account.asset"

    already_depreciated_amount_import = fields.Monetary(
        string="Already Depreciated Amount (Import)",
        currency_field="currency_id",
        default=0.0,
        help="Amount already depreciated in a previous system. "
        "This reduces the remaining depreciation schedule without "
        "changing the per-period depreciation rate.",
    )

    @api.constrains("already_depreciated_amount_import", "depreciation_base")
    def _check_already_depreciated_amount_import(self):
        for asset in self:
            if asset.already_depreciated_amount_import < 0:
                raise ValidationError(
                    _("Already Depreciated Amount (Import) must be >= 0.")
                )
            if asset.already_depreciated_amount_import > asset.depreciation_base:
                raise ValidationError(
                    _(
                        "Already Depreciated Amount (Import) cannot exceed "
                        "the depreciation base (%(base)s).",
                        base=asset.depreciation_base,
                    )
                )

    @api.depends(
        "depreciation_base",
        "depreciation_line_ids.type",
        "depreciation_line_ids.amount",
        "depreciation_line_ids.previous_id",
        "depreciation_line_ids.init_entry",
        "depreciation_line_ids.move_check",
        "already_depreciated_amount_import",
    )
    def _compute_depreciation(self):
        for asset in self:
            lines = asset.depreciation_line_ids.filtered(
                lambda l: l.type in ("depreciate", "remove")
                and (l.init_entry or l.move_check)
            )
            value_depreciated = (
                sum(line.amount for line in lines)
                + asset.already_depreciated_amount_import
            )
            residual = asset.depreciation_base - value_depreciated
            asset.update(
                {"value_residual": residual, "value_depreciated": value_depreciated}
            )

    def _compute_depreciation_amount_per_fiscal_year(
        self, table, line_dates, depreciation_start_date, depreciation_stop_date
    ):
        """Override to start fy_residual_amount reduced by the import amount."""
        self.ensure_one()
        # Temporarily reduce the starting residual so the FY loop stops earlier,
        # while keeping period_amount based on full depreciation_base so the
        # per-period rate stays consistent.
        import_amount = self.already_depreciated_amount_import
        if not import_amount:
            return super()._compute_depreciation_amount_per_fiscal_year(
                table, line_dates, depreciation_start_date, depreciation_stop_date
            )

        currency = self.company_id.currency_id
        fy_residual_amount = self.depreciation_base - import_amount
        i_max = len(table) - 1
        asset_sign = self.depreciation_base >= 0 and 1 or -1
        day_amount = 0.0
        if self.days_calc:
            days = (depreciation_stop_date - depreciation_start_date).days + 1
            day_amount = self.depreciation_base / days

        for i, entry in enumerate(table):
            if self.method_time == "year":
                # year_amount is still based on full depreciation_base via
                # _compute_year_amount — this keeps per-period rate stable
                year_amount = self._compute_year_amount(
                    fy_residual_amount,
                    depreciation_start_date,
                    depreciation_stop_date,
                    entry,
                )
                if self.method_period == "year":
                    period_amount = year_amount
                elif self.method_period == "quarter":
                    period_amount = year_amount / 4
                elif self.method_period == "month":
                    period_amount = year_amount / 12
                if i == i_max:
                    if self.method in ["linear-limit", "degr-limit"]:
                        fy_amount = fy_residual_amount - self.salvage_value
                    else:
                        fy_amount = fy_residual_amount
                else:
                    firstyear = i == 0 and True or False
                    fy_factor = self._get_fy_duration_factor(entry, firstyear)
                    fy_amount = year_amount * fy_factor
                if (
                    currency.compare_amounts(
                        asset_sign * (fy_amount - fy_residual_amount), 0
                    )
                    > 0
                ):
                    fy_amount = fy_residual_amount
                period_amount = currency.round(period_amount)
                fy_amount = currency.round(fy_amount)
            else:
                fy_amount = False
                if self.method_time == "number":
                    number = self.method_number
                else:
                    number = len(line_dates)
                period_amount = currency.round(self.depreciation_base / number)
            entry.update(
                {
                    "period_amount": period_amount,
                    "fy_amount": fy_amount,
                    "day_amount": day_amount,
                }
            )
            if self.method_time == "year":
                fy_residual_amount -= fy_amount
                if currency.is_zero(fy_residual_amount):
                    break
        i_max = i
        table = table[: i_max + 1]
        return table

    def _compute_depreciation_table_lines(
        self, table, depreciation_start_date, depreciation_stop_date, line_dates
    ):
        """Override to start with reduced remaining_value and non-zero depreciated_value."""
        self.ensure_one()
        import_amount = self.already_depreciated_amount_import
        if not import_amount:
            return super()._compute_depreciation_table_lines(
                table, depreciation_start_date, depreciation_stop_date, line_dates
            )

        currency = self.company_id.currency_id
        asset_sign = 1 if self.depreciation_base >= 0 else -1
        i_max = len(table) - 1
        remaining_value = self.depreciation_base - import_amount
        depreciated_value = import_amount
        company = self.company_id
        fiscalyear_lock_date = company.fiscalyear_lock_date or fields.Date.to_date(
            "1901-01-01"
        )

        for i, entry in enumerate(table):
            lines = []
            fy_amount_check = 0.0
            fy_amount = entry["fy_amount"]
            li_max = len(line_dates) - 1
            prev_date = max(entry["date_start"], depreciation_start_date)
            for li, line_date in enumerate(line_dates):
                line_days = (line_date - prev_date).days + 1
                if currency.is_zero(remaining_value):
                    break

                if line_date > min(
                    entry["date_stop"], depreciation_stop_date
                ) and not (i == i_max and li == li_max):
                    prev_date = line_date
                    break
                else:
                    prev_date = line_date + relativedelta(days=1)

                if (
                    self.method == "degr-linear"
                    and currency.compare_amounts(
                        asset_sign * (fy_amount - fy_amount_check), 0
                    )
                    < 0
                ):
                    break

                if i == 0 and li == 0:
                    if currency.compare_amounts(entry.get("day_amount"), 0) > 0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = self._get_first_period_amount(
                            table, entry, depreciation_start_date, line_dates
                        )
                        amount = currency.round(amount)
                else:
                    if currency.compare_amounts(entry.get("day_amount"), 0) > 0:
                        amount = line_days * entry.get("day_amount")
                    else:
                        amount = entry.get("period_amount")

                # last year, last entry — handle rounding deviations
                if i == i_max and li == li_max:
                    amount = remaining_value
                    remaining_value = 0.0
                else:
                    # Cap amount to remaining_value to prevent negative residual
                    if (
                        currency.compare_amounts(
                            asset_sign * amount,
                            asset_sign * remaining_value,
                        )
                        > 0
                    ):
                        amount = remaining_value
                    remaining_value -= amount
                fy_amount_check += amount
                line = {
                    "date": line_date,
                    "days": line_days,
                    "amount": amount,
                    "depreciated_value": depreciated_value,
                    "remaining_value": remaining_value,
                    "init": fiscalyear_lock_date >= line_date,
                }
                lines.append(line)
                depreciated_value += amount

            if self.method_time == "year" and not entry.get("day_amount"):
                if not currency.is_zero(fy_amount_check - fy_amount):
                    diff = fy_amount_check - fy_amount
                    amount = amount - diff
                    remaining_value += diff
                    lines[-1].update(
                        {"amount": amount, "remaining_value": remaining_value}
                    )
                    depreciated_value -= diff

            if not lines:
                table.pop(i)
            else:
                entry["lines"] = lines
            line_dates = line_dates[li:]

        for entry in table:
            if not entry["fy_amount"]:
                entry["fy_amount"] = sum(line["amount"] for line in entry["lines"])

    def compute_depreciation_board(self):
        """Override to include import amount in depreciated_value initialisation."""
        line_obj = self.env["account.asset.line"]

        for asset in self:
            import_amount = asset.already_depreciated_amount_import
            if not import_amount:
                # Delegate to super for assets without import amount
                super(AccountAsset, asset).compute_depreciation_board()
                continue

            currency = asset.company_id.currency_id
            if currency.is_zero(asset.value_residual):
                continue
            domain = [
                ("asset_id", "=", asset.id),
                ("type", "=", "depreciate"),
                "|",
                ("move_check", "=", True),
                ("init_entry", "=", True),
            ]
            posted_lines = line_obj.search(domain, order="line_date desc")
            if posted_lines:
                last_line = posted_lines[0]
            else:
                last_line = line_obj
            domain = [
                ("asset_id", "=", asset.id),
                ("type", "=", "depreciate"),
                ("move_id", "=", False),
                ("init_entry", "=", False),
            ]
            old_lines = line_obj.search(domain)
            if old_lines:
                old_lines.unlink()

            table = asset._compute_depreciation_table()
            if not table:
                continue

            asset._group_lines(table)

            depreciated_value_posted = depreciated_value = 0.0
            if posted_lines:
                total_table_lines = sum(len(entry["lines"]) for entry in table)
                move_check_lines = asset.depreciation_line_ids.filtered("move_check")
                last_depreciation_date = last_line.line_date
                last_date_in_table = table[-1]["lines"][-1]["date"]
                if (last_date_in_table < last_depreciation_date) or (
                    last_date_in_table == last_depreciation_date
                    and total_table_lines != len(move_check_lines)
                ):
                    raise UserError(
                        _(
                            "The duration of the asset conflicts with the "
                            "posted depreciation table entry dates."
                        )
                    )

                for _table_i, entry in enumerate(table):
                    residual_amount_table = entry["lines"][-1]["remaining_value"]
                    if (
                        entry["date_start"]
                        <= last_depreciation_date
                        <= entry["date_stop"]
                    ):
                        break

                if entry["date_stop"] == last_depreciation_date:
                    _table_i += 1
                    _line_i = 0
                else:
                    entry = table[_table_i]
                    date_min = entry["date_start"]
                    for _line_i, line in enumerate(entry["lines"]):
                        residual_amount_table = line["remaining_value"]
                        if date_min <= last_depreciation_date <= line["date"]:
                            break
                        date_min = line["date"]
                    if line["date"] == last_depreciation_date:
                        _line_i += 1
                table_i_start = _table_i
                line_i_start = _line_i

                depreciated_value_posted = depreciated_value = (
                    sum(posted_line.amount for posted_line in posted_lines)
                    + import_amount
                )
                residual_amount = asset.depreciation_base - depreciated_value
                amount_diff = currency.round(residual_amount_table - residual_amount)
                if amount_diff:
                    if len(move_check_lines) == total_table_lines:
                        table[table_i_start]["lines"].append(
                            table[table_i_start]["lines"][line_i_start - 1]
                        )
                        line = table[table_i_start]["lines"][line_i_start]
                        line["days"] = 0
                        line["amount"] = amount_diff
                    line = table[table_i_start]["lines"][line_i_start]
                    line["amount"] -= amount_diff

            else:
                table_i_start = 0
                line_i_start = 0
                depreciated_value_posted = import_amount

            asset._compute_depreciation_line(
                depreciated_value_posted,
                table_i_start,
                line_i_start,
                table,
                last_line,
                posted_lines,
            )
        return True
