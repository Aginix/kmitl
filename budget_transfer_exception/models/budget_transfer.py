from odoo import _, api, models


class BudgetTransfer(models.Model):
    """Gate the transfer confirm (ยืนยัน) with the OCA ``base.exception`` framework.

    This is the framework layer only — it wires ``base.exception`` onto
    ``budget.transfer`` (the ยืนยัน hook, the review popup, the reset clearing)
    and offers a generic source-model alignment helper. It ships *no*
    ``exception.rule`` of its own; the concrete checks live in thin bridge modules
    (``budget_transfer_exception_kmitl_project`` /
    ``budget_transfer_exception_procurement_plan``), each of which depends on its
    own source module and registers one rule + one detection method here.

    The alignment idea a bridge encodes: a project / procurement-plan budget code
    does not stand on its own — its budget lives inside a specific source record
    that pins the budget code, the fiscal year, *and* the accounting dimensions
    the budget was reserved against; a transfer touching such a code must match
    that source.
    """

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "base.exception"]
    # Keep the transfer's own ordering — mixing in base.exception would otherwise
    # pull its "main_exception_id asc" _order (same guard as kmitl_project).
    _order = "date desc, name desc, id desc"

    # The four core dimensions share the same field name on the transfer line and
    # on both source models, so one map covers every bridge's check.
    _SOURCE_DIM_FIELDS = (
        ("department_analytic_id", "ส่วนงาน"),
        ("source_analytic_id", "แหล่งเงิน"),
        ("activity_analytic_id", "กิจกรรม"),
        ("fund_analytic_id", "กองทุน"),
    )

    # ------------------------------------------------------------------
    # base.exception plumbing
    # ------------------------------------------------------------------
    @api.model
    def _reverse_field(self):
        return "budget_transfer_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "budget_transfer_exception.action_budget_transfer_exception_confirm"
        )

    # ------------------------------------------------------------------
    # Confirm hook (ยืนยัน)
    # ------------------------------------------------------------------
    def action_submit(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit()

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        # A fresh draft must re-earn its confirmation — drop any detected/ignored
        # exceptions so the check runs again on the next ยืนยัน.
        for transfer in self:
            transfer.exception_ids = False
            transfer.main_exception_id = False
            transfer.ignore_exception = False
        return res

    # ------------------------------------------------------------------
    # Generic source-model alignment (driven by a bridge-supplied spec)
    # ------------------------------------------------------------------
    def _transfer_source_mismatches(self, spec):
        """Return a message per misaligned line for the given source ``spec``.

        ``spec`` is a dict a bridge supplies:
        ``{"flag", "tag_field", "model", "label"}`` — the line flag that marks the
        source type, the line's dimension tag field, the source model, and a Thai
        label. Empty list ⇒ aligned. The list's mere non-emptiness drives the rule.
        """
        self.ensure_one()
        messages = []
        for line in self.line_ids.filtered("transfer_direction"):
            if line[spec["flag"]]:
                messages.extend(self._line_source_mismatches(line, spec))
        return messages

    def _line_source_mismatches(self, line, spec):
        """Match one project / procurement-plan line to its source record."""
        direction = (
            _("โอนออก") if line.transfer_direction == "from" else _("โอนเข้า")
        )
        label = spec["label"]
        tag = line[spec["tag_field"]]
        if not tag:
            return [
                _(
                    "รายการโอน (%(direction)s) รหัสงบประมาณ %(account)s เป็นประเภท"
                    "%(label)s แต่ยังไม่ได้ระบุมิติ%(label)s"
                )
                % {
                    "direction": direction,
                    "account": line.account_id.display_name or "-",
                    "label": label,
                }
            ]

        source = self.env[spec["model"]].search(
            [("analytic_account_id", "=", tag.id)], limit=1
        )
        if not source:
            return [
                _(
                    "รายการโอน (%(direction)s) ไม่พบข้อมูล%(label)sต้นทางที่ตรงกับ"
                    "มิติ '%(tag)s'"
                )
                % {"direction": direction, "label": label, "tag": tag.display_name}
            ]

        mismatches = []
        if source.budget_account_id != line.account_id:
            mismatches.append(
                _("รหัสงบประมาณ (ต้นทาง: %(src)s / โอน: %(line)s)")
                % {
                    "src": source.budget_account_id.display_name or "-",
                    "line": line.account_id.display_name or "-",
                }
            )
        # The fiscal year is header-owned on a transfer; the budget the source
        # reserved belongs to its own year, so the two must be the same year.
        if source.account_fiscal_year_id != self.account_fiscal_year_id:
            mismatches.append(
                _("ปีงบประมาณ (ต้นทาง: %(src)s / โอน: %(line)s)")
                % {
                    "src": source.account_fiscal_year_id.display_name or "-",
                    "line": self.account_fiscal_year_id.display_name or "-",
                }
            )
        for fname, dim_label in self._SOURCE_DIM_FIELDS:
            if source[fname] != line[fname]:
                mismatches.append(
                    _("%(label)s (ต้นทาง: %(src)s / โอน: %(line)s)")
                    % {
                        "label": dim_label,
                        "src": source[fname].display_name or "-",
                        "line": line[fname].display_name or "-",
                    }
                )
        if not mismatches:
            return []
        return [
            _(
                "รายการโอน (%(direction)s) ไม่ตรงกับ%(label)sต้นทาง '%(source)s': "
                "%(mismatches)s"
            )
            % {
                "direction": direction,
                "label": label,
                "source": source.display_name,
                "mismatches": ", ".join(mismatches),
            }
        ]
