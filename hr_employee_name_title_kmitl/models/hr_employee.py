from odoo import api, models

# Mirror kmitl_hr_employee_full_name's placeholder for an employee with no name.
NO_NAME_TEXT = "Untitled"

# Writing any of these fields can change the derived employee name, so a write
# touching them must re-derive ``name``.  ``academic_standing_title`` is itself a
# stored-computed field derived from the academic fields listed here, so we react
# to its inputs (the write that changes them flushes the title before we read it).
TITLE_SYNC_TRIGGER_FIELDS = frozenset(
    (
        "academic_standing_id",
        "rank_id",
        "rank_nobility_id",
        "profession_id",
        "education_level_id",
        "role",
        "prefix_id",
        "firstname",
        "middlename",
        "lastname",
        "name",
    )
)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # ------------------------------------------------------------------
    # Title prefix by work track (role)
    # ------------------------------------------------------------------
    def _get_title_prefix(self, lang="th"):
        """Return the title prefix placed before the employee's name.

        Academic-track employees are addressed by their academic standing title;
        everyone else (support track or no track) by their personal honorific
        (prefix_id, e.g. นาย/นาง/นางสาว).  ``lang="en"`` returns the English
        variants (the honorific is translatable, so it is read in ``en_US``).
        """
        self.ensure_one()
        if lang == "en":
            if self.role == "academic" and self.academic_standing_title_en:
                return self.academic_standing_title_en
            return self.prefix_id.with_context(lang="en_US").name or ""
        if self.role == "academic" and self.academic_standing_title:
            return self.academic_standing_title
        # prefix_id.name is translatable: force Thai so the honorific never comes
        # out in the UI user's language.
        return self.prefix_id.with_context(lang="th_TH").name or ""

    # ------------------------------------------------------------------
    # Thai name — derived through the (related) ``name`` field
    # ------------------------------------------------------------------
    def _build_name_with_title(self):
        """Thai name = ``{prefix}{firstname} {middlename} {lastname}``.

        The prefix is glued directly to the first name (no separating space);
        when there are no name parts the full_name placeholder is kept.
        """
        self.ensure_one()
        base = self._get_name(self.firstname, self.middlename, self.lastname)
        if not base:
            return NO_NAME_TEXT
        prefix = self._get_title_prefix("th")
        return "%s%s" % (prefix, base) if prefix else base

    def _sync_name_title(self):
        """Write the derived name onto each record (flows to resource.name)."""
        for rec in self:
            new_name = rec._build_name_with_title()
            if rec.name != new_name:
                rec.with_context(skip_name_title_sync=True).write({"name": new_name})

    @api.onchange("firstname", "middlename", "lastname")
    def _onchange_firstname_middlename_lastname(self):
        # Override full_name's preview so the form shows the title live while
        # editing the name parts, instead of a title-less name until save.
        self.name = self._build_name_with_title()

    @api.onchange(
        "prefix_id",
        "role",
        "academic_standing_id",
        "rank_id",
        "rank_nobility_id",
        "profession_id",
    )
    def _onchange_name_title_preview(self):
        # Live preview of the derived name when the title inputs change.
        self.name = self._build_name_with_title()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_name_title()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_name_title_sync") and (
            TITLE_SYNC_TRIGGER_FIELDS & set(vals)
        ):
            self._sync_name_title()
        return res

    # ------------------------------------------------------------------
    # Drop the inverse: a prefixed name must never be split back into parts
    # ------------------------------------------------------------------
    def _prepare_vals_on_write_firstname_middlename_lastname(self, vals):
        # Keep the forward direction (parts -> name); drop the reverse
        # (name -> parts) so writing a prefixed name cannot push the title into
        # firstname.  The name is derived, never inverse-split.
        if "firstname" in vals or "middlename" in vals or "lastname" in vals:
            return super()._prepare_vals_on_write_firstname_middlename_lastname(vals)

    def _inverse_name(self):
        return

    # ------------------------------------------------------------------
    # English name — override full_name's compute to prepend the title
    # ------------------------------------------------------------------
    @api.depends(
        "firstname_secondary",
        "middlename_secondary",
        "lastname_secondary",
        "role",
        "academic_standing_title_en",
        "prefix_id",
    )
    def _compute_name_secondary(self):
        for rec in self:
            base = rec._get_name(
                rec.firstname_secondary,
                rec.middlename_secondary,
                rec.lastname_secondary,
            )
            if not base:
                rec.name_secondary = ""
                continue
            prefix = rec._get_title_prefix("en")
            # English keeps a space between the title and the name.
            rec.name_secondary = "%s %s" % (prefix, base) if prefix else base
