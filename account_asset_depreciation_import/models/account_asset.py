# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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

    def _find_import_start_position(self, table, import_amount, currency):
        """Walk the standard depreciation table and find where the import
        amount is exhausted.  Returns ``(table_i, line_i)`` — the position
        of the first *future* line.  The line at that position has its
        ``amount`` adjusted to the portion not covered by the import.
        """
        accumulated = 0.0
        for ti, entry in enumerate(table):
            for li, line in enumerate(entry["lines"]):
                accumulated += line["amount"]
                if currency.compare_amounts(accumulated, import_amount) > 0:
                    # Import falls in the middle of this line — adjust
                    line["amount"] = currency.round(accumulated - import_amount)
                    return ti, li
                if currency.is_zero(accumulated - import_amount):
                    # Import exactly covers through this line — next one
                    li_next = li + 1
                    if li_next >= len(entry["lines"]):
                        return ti + 1, 0
                    return ti, li_next
        # Import covers everything (constraint should prevent this)
        return len(table), 0

    def _compute_depreciation_table(self):
        """Override to return a table that starts after the imported amount.

        The standard table is computed in full, then all lines covered by
        ``already_depreciated_amount_import`` are removed and the first
        remaining line's amount is adjusted for partial coverage.
        ``depreciated_value`` / ``remaining_value`` on every kept line are
        recalculated so they start from the import amount.
        """
        table = super()._compute_depreciation_table()
        import_amount = self.already_depreciated_amount_import
        if not import_amount or not table:
            return table
        currency = self.company_id.currency_id
        ti, li = self._find_import_start_position(table, import_amount, currency)
        if ti >= len(table):
            return []
        table = table[ti:]
        if li > 0:
            table[0]["lines"] = table[0]["lines"][li:]
        # Recalculate cumulative values starting from the import amount.
        dep_val = import_amount
        rem_val = self.depreciation_base - dep_val
        for entry in table:
            for line in entry["lines"]:
                line["depreciated_value"] = dep_val
                rem_val -= line["amount"]
                line["remaining_value"] = rem_val
                dep_val += line["amount"]
        return table

    def compute_depreciation_board(self):
        """Override to pass the import amount as the initial depreciated value."""
        line_obj = self.env["account.asset.line"]

        for asset in self:
            import_amount = asset.already_depreciated_amount_import
            if not import_amount:
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

            # Table already trimmed to future lines by _compute_depreciation_table.
            table = asset._compute_depreciation_table()
            if not table:
                continue

            asset._group_lines(table)

            depreciated_value_posted = depreciated_value = 0.0
            if posted_lines:
                # --- posted lines exist --------------------------------
                # Standard logic: find starting position by date.
                # Adding import_amount to depreciated_value_posted aligns
                # the residual comparison with the trimmed table's values.
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
                amount_diff = currency.round(
                    residual_amount_table - residual_amount
                )
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
                # --- no posted lines -----------------------------------
                # Table already starts at the first future line.
                table_i_start = line_i_start = 0
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
