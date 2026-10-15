from collections import defaultdict

from odoo import api, models


class BudgetDashboard(models.AbstractModel):
    """List Pool Tag items (โครงการ/แผน) under each budget code of the report.

    Generic engine: no tag is known here. The module that owns a Pool Tag
    registers it by overriding :meth:`_pool_tags` (``super()`` + append), the
    same open-for-extension shape as ``_overview_sections``.

    Items hang only under the budget code whose lines carry them (never rolled
    up to ancestor codes, which already include them in their own figures). Per
    code a residual "ไม่ระบุโครงการ/แผน" row carries the untagged remainder, so
    the item rows always add up to the code row's own figures.

    Opt-in per call (context ``pool_tag_rows``): the tag fields join the
    report's own grouping (``_dashboard_extra_fields``), so item figures come
    from the same queries as the code rows and are spliced in server-side
    (``_dashboard_extra_rows``). Other callers (reservation picker, overview)
    are unaffected.
    """

    _inherit = "budget.dashboard"

    _POOL_TAG_UNTAGGED_NAME = "ไม่ระบุโครงการ/แผน"
    _POOL_TAG_NO_ACCESS_NAME = "(ไม่มีสิทธิ์ดูรายการ)"

    def _pool_tags(self):
        """Registered Pool Tags, in display order.

        Each entry: ``{"field", "label", "res_model", "res_field"}`` —
        ``field`` is the stored tag field on budget move /
        commitment lines; ``res_model`` / ``res_field`` locate the owning
        document (e.g. ``kmitl.project`` by ``analytic_account_id``).
        """
        return []

    @api.model
    def get_pool_tags(self):
        """Registered tags for the front end's single toggle: ``[{field, label}]``."""
        return [
            {"field": tag["field"], "label": tag["label"]} for tag in self._pool_tags()
        ]

    @api.model
    def get_reservation_grid(self, *args, **kwargs):
        # Item rows are never selectable: keep them out of the picker feed.
        return super(
            BudgetDashboard, self.with_context(pool_tag_rows=False)
        ).get_reservation_grid(*args, **kwargs)

    def _dashboard_extra_fields(self):
        fields = super()._dashboard_extra_fields()
        if self.env.context.get("pool_tag_rows"):
            fields = fields + [tag["field"] for tag in self._pool_tags()]
        return fields

    def _dashboard_extra_rows(self, rows, facts, dims):
        rows = super()._dashboard_extra_rows(rows, facts, dims)
        if not self.env.context.get("pool_tag_rows"):
            return rows
        items = self._pool_tag_rows(facts, dims)
        if not items:
            return rows
        out = []
        for row in rows:
            out.append(row)
            if row["row_type"] != "account":
                continue
            row_dims = row.get("dims") or {}
            own = items.get(
                (row["account_id"], tuple(row_dims.get(d) or 0 for d in dims))
            )
            if not own:
                continue
            # Codes with no child accounts get their caret from the items only;
            # the front end drops it while items are hidden.
            row["pool_tag_leaf"] = not row["has_children"]
            row["has_children"] = True
            for item in own:
                out.append(
                    dict(
                        item,
                        id=False,
                        key="%s|t%s%s"
                        % (
                            row["key"],
                            item["tag_field"] or "none",
                            item["analytic_id"] or 0,
                        ),
                        parent_key=row["key"],
                        level=row["level"] + 1,
                    )
                )
        return out

    def _pool_tag_rows(self, facts, dims):
        """{(account_id, breakdown_tuple): [item row]} from the full ``facts``.

        ``facts`` are grouped by ``dims`` + ``_dashboard_extra_fields()``; the
        Pool Tag fields are located among the extra positions by name.
        """
        tags = self._pool_tags()
        if not tags:
            return {}
        all_fields = dims + self._dashboard_extra_fields()
        tag_names = [t["field"] for t in tags]
        tag_pos = [all_fields.index(name) for name in tag_names]
        n = len(dims)

        # own[(account_id, breakdown_tuple)][(tag_field, analytic_id)] = values.
        # A line carrying two tags is assigned to the first one only, so no
        # amount is ever counted twice; (False, 0) is the untagged remainder.
        own = defaultdict(dict)
        for metric, values in facts.items():
            for (acc_id, tup), val in values.items():
                item = (False, 0)
                for field, pos in zip(tag_names, tag_pos):
                    if tup[pos]:
                        item = (field, tup[pos])
                        break
                bucket = own[(acc_id, tup[:n])]
                vals = bucket.setdefault(item, dict.fromkeys(facts, 0.0))
                vals[metric] += val

        tagged_ids = {
            tag_id for bucket in own.values() for (field, tag_id) in bucket if field
        }
        # Only analytic accounts the user may read are named; the rest keep
        # their figures under the document's name or a no-access label.
        analytic = {
            a.id: a
            for a in self.env["account.analytic.account"]
            .browse(list(tagged_ids))
            ._filter_access_rules("read")
        }
        docs = self._pool_tag_documents(tags, tagged_ids)
        tag_order = {name: i for i, name in enumerate(tag_names)}

        out = {}
        for (acc_id, bd), bucket in own.items():
            if not any(field for field, _tag_id in bucket):
                continue  # nothing tagged on this code: no item rows
            columns = {it: self._value_columns(vals) for it, vals in bucket.items()}
            if not any(self._pool_tag_has_value(c) for c in columns.values()):
                continue  # all-zero items carry nothing (and no empty caret)
            items = sorted(
                bucket,
                key=lambda it: (
                    not it[0],  # untagged remainder last
                    tag_order.get(it[0], 0),
                    (analytic[it[1]].code or "") if it[1] in analytic else "",
                ),
            )
            rows = []
            for field, tag_id in items:
                rec = analytic.get(tag_id)
                res_model, res_id, doc_name = docs.get(tag_id, (False, False, ""))
                if rec:
                    name = rec.name
                elif doc_name:
                    # analytic hidden by OU rules but the document is readable
                    name = doc_name
                elif field:
                    name = self._POOL_TAG_NO_ACCESS_NAME
                else:
                    name = self._POOL_TAG_UNTAGGED_NAME
                rows.append(
                    {
                        "row_type": "pool_tag",
                        "account_id": acc_id,
                        "dims": {dims[i]: (bd[i] or False) for i in range(n)},
                        "tag_field": field,
                        "analytic_id": tag_id or False,
                        "code": (rec.code or "") if rec else "",
                        "name": name,
                        "res_model": res_model,
                        "res_id": res_id,
                        "has_children": False,
                        **columns[(field, tag_id)],
                    }
                )
            out[(acc_id, bd)] = rows
        return out

    @staticmethod
    def _pool_tag_has_value(columns):
        return any(abs(val) > 0.005 for val in columns.values())

    def _pool_tag_documents(self, tags, analytic_ids):
        """analytic id -> (res_model, res_id, display_name) of the owning
        project / plan.

        Plain searches (never ``sudo``): a document the user cannot read is
        simply not linked, so its name renders as plain text. Archived
        documents are included, since their money still shows in the report.
        """
        out = {}
        if not analytic_ids:
            return out
        for tag in tags:
            model_name = tag.get("res_model")
            if not model_name or model_name not in self.env:
                continue
            Model = self.env[model_name]
            if not Model.check_access_rights("read", raise_exception=False):
                continue
            res_field = tag.get("res_field") or "analytic_account_id"
            docs = Model.with_context(active_test=False).search(
                [(res_field, "in", list(analytic_ids))]
            )
            for doc in docs:
                out.setdefault(
                    doc[res_field].id, (model_name, doc.id, doc.display_name)
                )
        return out
