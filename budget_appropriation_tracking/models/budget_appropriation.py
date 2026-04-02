from markupsafe import Markup, escape

from odoo import _, models

# Fields on budget.appropriation.line to track for value changes
_TRACKED_FIELDS = {
    "account_id": "รหัสงบประมาณ",
    "description": "รายละเอียด",
    "balance": "จำนวนเงิน",
    "note": "หมายเหตุ",
    "activity_analytic_id": "กิจกรรม",
    "fund_analytic_id": "กองทุน",
}
_M2O_FIELDS = {"account_id", "activity_analytic_id", "fund_analytic_id"}


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    def write(self, vals):
        track = not self.env.context.get("tracking_disable") and (
            "line_ids" in vals or "deduct_line_ids" in vals
        )

        snapshots = {}
        if track:
            for rec in self:
                snapshots[rec.id] = rec._snapshot_appropriation_lines()

        result = super().write(vals)

        if track:
            for rec in self:
                old_snap = snapshots.get(rec.id)
                if old_snap is not None:
                    new_snap = rec._snapshot_appropriation_lines()
                    body = rec._build_line_tracking_body(old_snap, new_snap)
                    if body:
                        rec._message_log(body=body)

        return result

    # -- snapshot --

    def _snapshot_appropriation_lines(self):
        """Capture current state of all lines for before/after comparison."""
        snapshot = {}
        for line in self.line_ids | self.deduct_line_ids:
            data = {
                "deduct": line.deduct,
                "code": line.code or "",
                "name": line.name or "",
            }
            for fname in _TRACKED_FIELDS:
                val = line[fname]
                if fname in _M2O_FIELDS:
                    data[fname] = val.id if val else False
                    data[f"{fname}_display"] = val.display_name if val else ""
                elif fname == "balance":
                    data[fname] = val or 0.0
                else:
                    data[fname] = val or ""
            snapshot[line.id] = data
        return snapshot

    # -- message building --

    def _build_line_tracking_body(self, old_snap, new_snap):
        """Build a single HTML message describing all line changes."""
        old_ids = set(old_snap)
        new_ids = set(new_snap)

        parts = []

        # Created lines
        for lid in sorted(new_ids - old_ids):
            d = new_snap[lid]
            label = self._line_label(d)
            parts.append(_("%(label)s added: %(desc)s", label=label, desc=self._fmt_line(d)))

        # Updated lines
        for lid in sorted(old_ids & new_ids):
            changes = self._diff_line(old_snap[lid], new_snap[lid])
            if changes:
                d = new_snap[lid]
                label = self._line_label(d)
                parts.append(
                    _(
                        "%(label)s %(desc)s updated: %(changes)s",
                        label=label,
                        desc=self._fmt_line(d),
                        changes=changes,
                    )
                )

        # Deleted lines
        for lid in sorted(old_ids - new_ids):
            d = old_snap[lid]
            label = self._line_label(d)
            parts.append(_("%(label)s removed: %(desc)s", label=label, desc=self._fmt_line(d)))

        if not parts:
            return False

        items = Markup("").join(Markup("<li>%s</li>") % escape(str(p)) for p in parts)
        return Markup("<ul>%s</ul>") % items

    # -- formatting helpers --

    @staticmethod
    def _line_label(data):
        return _("Deduct Line") if data["deduct"] else _("Line")

    @staticmethod
    def _fmt_line(data):
        parts = [p for p in (data.get("code"), data.get("name")) if p]
        desc = " ".join(parts)
        balance = data.get("balance")
        if balance:
            desc += " - {:,.2f}".format(balance)
        return desc

    @staticmethod
    def _diff_line(old, new):
        changes = []
        for fname, label in _TRACKED_FIELDS.items():
            old_val = old.get(fname)
            new_val = new.get(fname)
            if old_val != new_val:
                old_disp = _fmt_field(fname, old)
                new_disp = _fmt_field(fname, new)
                changes.append("{}: {} → {}".format(label, old_disp, new_disp))
        return ", ".join(changes)


def _fmt_field(fname, data):
    if fname == "balance":
        return "{:,.2f}".format(data.get(fname, 0))
    if fname in _M2O_FIELDS:
        return data.get(f"{fname}_display") or _("(empty)")
    return data.get(fname) or _("(empty)")
