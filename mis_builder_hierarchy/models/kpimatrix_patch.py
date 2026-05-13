"""Monkey-patch KpiMatrix / KpiMatrixRow to support hierarchical source data.

When a KPI has `auto_expand_accounts_hierarchical=True` and its source model
exposes a self-referencing parent_id (with parent_path / _parent_store), this
patch walks the parent chain from each leaf account, creates intermediate
parent rows on the matrix, rolls up child values bottom-up, and emits row
metadata (row_key / parent_row_key / has_children) for the OWL widget.

Depth is folded into `style_props["indent_level"]` so the existing
`mis.report.style.to_css_style` / `to_xlsx_style` paths render indentation
automatically — no separate QWeb or XLSX override is needed.

KpiMatrix / KpiMatrixRow are plain Python classes, not Odoo models, so
`_inherit` is unavailable; monkey-patching is the only entry point.
"""

from collections import defaultdict

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.kpimatrix import KpiMatrix, KpiMatrixRow


def _hierarchy_enabled(kpi):
    return bool(
        getattr(kpi, "auto_expand_accounts", False)
        and getattr(kpi, "auto_expand_accounts_hierarchical", False)
    )


def _get_parent_field(model):
    parent_name = getattr(model, "_parent_name", "parent_id")
    field = model._fields.get(parent_name)
    if field and getattr(field, "comodel_name", None) == model._name:
        return parent_name
    return None


_orig_row_init = KpiMatrixRow.__init__


def _patched_row_init(self, matrix, kpi, account_id=None, parent_row=None):
    _orig_row_init(self, matrix, kpi, account_id, parent_row)
    self.parent_account_id = None


KpiMatrixRow.__init__ = _patched_row_init


def _load_hierarchy(self, kpi):
    """Resolve the full ancestor set of leaf accounts via parent_path.

    Returns (parents, depths) — both keyed by account_id. `parents[id]` is
    the direct parent id (or None); `depths[id]` is the absolute hierarchy
    depth (root = 0).
    """
    detail_rows = self._detail_rows.get(kpi) or {}
    leaf_ids = list(detail_rows.keys())
    if not leaf_ids:
        return {}, {}

    leaf_recs = self._account_model.browse(leaf_ids).read(["parent_path"])
    own_paths = {}
    extra_ids = set()
    for r in leaf_recs:
        path = (r.get("parent_path") or "").strip("/")
        ids = [int(x) for x in path.split("/")] if path else [r["id"]]
        own_paths[r["id"]] = ids
        extra_ids.update(ids)
    extra_ids -= set(leaf_ids)
    if extra_ids:
        extra_recs = self._account_model.browse(list(extra_ids)).read(["parent_path"])
        for r in extra_recs:
            path = (r.get("parent_path") or "").strip("/")
            ids = [int(x) for x in path.split("/")] if path else [r["id"]]
            own_paths[r["id"]] = ids

    parents = {}
    depths = {}
    for rec_id, ids in own_paths.items():
        parents[rec_id] = ids[-2] if len(ids) > 1 else None
        depths[rec_id] = len(ids) - 1
    return parents, depths


def _expand_hierarchical(self, kpi):
    """Create intermediate parent rows; assign indent_level + parent_account_id."""
    if not _hierarchy_enabled(kpi):
        return
    detail_rows = self._detail_rows.get(kpi)
    if not detail_rows:
        return
    if not _get_parent_field(self._account_model):
        return

    parents, depths = _load_hierarchy(self, kpi)
    if not parents:
        return

    kpi_row = self._kpi_rows[kpi]
    for account_id in parents:
        if account_id not in detail_rows:
            detail_rows[account_id] = KpiMatrixRow(
                self, kpi, account_id, parent_row=kpi_row
            )
        row = detail_rows[account_id]
        row.parent_account_id = parents[account_id]
        base = row.style_props.get("indent_level") or 0
        row.style_props["indent_level"] = base + depths[account_id]

    children = defaultdict(list)
    for acc_id, parent in parents.items():
        if parent and parent in detail_rows:
            children[parent].append(acc_id)
    self._hierarchy_children[kpi] = dict(children)


def _accumulate(vals):
    acc = AccountingNone
    for v in vals:
        if v is AccountingNone or v is None:
            continue
        acc = v if acc is AccountingNone else acc + v
    return acc


def _rollup_hierarchical(self, kpi):
    """Bottom-up sum: parent_value = own_value + sum(child_values), per column."""
    if not _hierarchy_enabled(kpi):
        return
    if not getattr(kpi, "auto_expand_accounts_rollup", True):
        return
    children = self._hierarchy_children.get(kpi) or {}
    if not children:
        return
    detail_rows = self._detail_rows[kpi]

    order = []
    visited = set()

    def _post_order(acc_id):
        if acc_id in visited:
            return
        visited.add(acc_id)
        for c in children.get(acc_id, ()):
            _post_order(c)
        order.append(acc_id)

    for acc_id in detail_rows:
        _post_order(acc_id)

    resolved_cols = [(k, c) for k, c in self._cols.items() if c is not None]

    for parent_id in order:
        kids = children.get(parent_id)
        if not kids:
            continue
        parent_row = detail_rows[parent_id]
        for col_key, col in resolved_cols:
            parent_tuple = col.get_cell_tuple_for_row(parent_row)
            new_vals = []
            for i in range(col.colspan):
                own = (
                    parent_tuple[i].val
                    if parent_tuple and parent_tuple[i] is not None
                    else AccountingNone
                )
                child_vals = [
                    col.get_cell_tuple_for_row(detail_rows[c])[i].val
                    for c in kids
                    if col.get_cell_tuple_for_row(detail_rows[c]) is not None
                    and col.get_cell_tuple_for_row(detail_rows[c])[i] is not None
                ]
                new_vals.append(_accumulate([own] + child_vals))
            self.set_values_detail_account(
                kpi, col_key, parent_id, new_vals,
                [None] * col.colspan, tooltips=False,
            )


def _expand_and_rollup_all(self):
    if getattr(self, "_hierarchy_expanded", False):
        return
    self._hierarchy_children = {}
    for kpi in list(self._detail_rows.keys()):
        self._expand_hierarchical(kpi)
        self._rollup_hierarchical(kpi)
    self._hierarchy_expanded = True


KpiMatrix._expand_hierarchical = _expand_hierarchical
KpiMatrix._rollup_hierarchical = _rollup_hierarchical
KpiMatrix._expand_and_rollup_all = _expand_and_rollup_all


_orig_compute_comparisons = KpiMatrix.compute_comparisons


def _patched_compute_comparisons(self):
    self._expand_and_rollup_all()
    _orig_compute_comparisons(self)


KpiMatrix.compute_comparisons = _patched_compute_comparisons


_orig_iter_rows = KpiMatrix.iter_rows


def _patched_iter_rows(self):
    has_hierarchy = any(
        _hierarchy_enabled(kpi) for kpi in self._detail_rows
    )
    if not has_hierarchy:
        yield from _orig_iter_rows(self)
        return

    for kpi_row in self._kpi_rows.values():
        yield kpi_row
        detail_rows = self._detail_rows[kpi_row.kpi]
        if not detail_rows:
            continue
        if not _hierarchy_enabled(kpi_row.kpi):
            for row in sorted(detail_rows.values(), key=lambda r: r.label):
                yield row
            continue
        children = self._hierarchy_children.get(kpi_row.kpi) or {}
        roots = sorted(
            (
                acc_id for acc_id, row in detail_rows.items()
                if not row.parent_account_id
                or row.parent_account_id not in detail_rows
            ),
            key=lambda i: detail_rows[i].label,
        )
        visited = set()

        def _walk(acc_id):
            if acc_id in visited:
                return
            visited.add(acc_id)
            yield detail_rows[acc_id]
            for child_id in sorted(
                children.get(acc_id, ()),
                key=lambda i: detail_rows[i].label,
            ):
                yield from _walk(child_id)

        for root_id in roots:
            yield from _walk(root_id)


KpiMatrix.iter_rows = _patched_iter_rows


_orig_as_dict = KpiMatrix.as_dict


def _patched_as_dict(self):
    result = _orig_as_dict(self)
    visible_rows = [
        r for r in self.iter_rows()
        if not (
            (r.style_props.hide_empty and r.is_empty()) or r.style_props.hide_always
        )
    ]
    if len(visible_rows) != len(result["body"]):
        return result
    children_lookup = self._hierarchy_children or {}
    for row_data, row in zip(visible_rows, result["body"]):
        kpi = row.kpi
        hierarchical = _hierarchy_enabled(kpi) and row.account_id is not None
        if hierarchical:
            row_data["row_key"] = KpiMatrix._make_row_key(kpi.id, row.account_id)
            parent_acc = row.parent_account_id
            row_data["parent_row_key"] = (
                KpiMatrix._make_row_key(kpi.id, parent_acc) if parent_acc else None
            )
            row_data["has_children"] = bool(
                children_lookup.get(kpi, {}).get(row.account_id)
            )
        else:
            row_data["row_key"] = None
            row_data["parent_row_key"] = None
            row_data["has_children"] = False
    return result


KpiMatrix.as_dict = _patched_as_dict


def _make_row_key(kpi_id, account_id):
    return "{}#{}".format(kpi_id, account_id)


KpiMatrix._make_row_key = staticmethod(_make_row_key)
