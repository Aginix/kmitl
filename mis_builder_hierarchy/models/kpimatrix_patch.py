"""Monkey-patch KpiMatrix / KpiMatrixRow to support hierarchical source data.

The base mis_builder treats account-detail rows as a flat list sorted by label.
This patch:

1. Tags each row with a `level` attribute (KPI row = 0, leaf detail = 1, deeper levels increase).
2. After all periods are computed, walks the source model's parent_id chain
   from each leaf detail row, creating intermediate parent rows as needed.
3. Optionally rolls up child values into parents (bottom-up sum).
4. Sorts detail rows in tree order (depth-first, sequence then label per level).
5. Exposes hierarchy metadata via `as_dict()` for the OWL widget / QWeb / XLSX renderers.

KpiMatrix and KpiMatrixRow are plain Python classes (not Odoo models), so monkey patching
is the only way to extend them without touching upstream code.
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
    self.level = 0 if account_id is None else 1
    self.parent_account_id = None


KpiMatrixRow.__init__ = _patched_row_init


def _expand_hierarchical(self, kpi):
    """Create intermediate parent rows for accounts that have a parent_id chain."""
    if not _hierarchy_enabled(kpi):
        return
    detail_rows = self._detail_rows.get(kpi)
    if not detail_rows:
        return
    parent_field = _get_parent_field(self._account_model)
    if not parent_field:
        return

    seen = set(detail_rows.keys())
    to_load = list(seen)
    parents = {}
    while to_load:
        records = self._account_model.browse(to_load).exists()
        next_load = []
        for rec in records:
            parent = rec[parent_field]
            pid = parent.id if parent else None
            parents[rec.id] = pid
            if pid and pid not in seen:
                seen.add(pid)
                next_load.append(pid)
        to_load = next_load

    kpi_row = self._kpi_rows[kpi]
    for account_id in seen:
        if account_id not in detail_rows:
            new_row = KpiMatrixRow(self, kpi, account_id, parent_row=kpi_row)
            detail_rows[account_id] = new_row
        detail_rows[account_id].parent_account_id = parents.get(account_id)

    def _depth(acc_id, memo, stack):
        if acc_id in memo:
            return memo[acc_id]
        if acc_id in stack:
            return 0
        parent = parents.get(acc_id)
        if not parent or parent not in detail_rows:
            memo[acc_id] = 0
            return 0
        stack.add(acc_id)
        d = _depth(parent, memo, stack) + 1
        stack.discard(acc_id)
        memo[acc_id] = d
        return d

    memo = {}
    for acc_id, row in detail_rows.items():
        depth = _depth(acc_id, memo, set())
        row.level = depth + 1
        if isinstance(row.style_props, dict):
            row.style_props["_hierarchy_level"] = depth


def _rollup_hierarchical(self, kpi):
    """Bottom-up sum: each parent row's value += sum of its children's values."""
    if not _hierarchy_enabled(kpi):
        return
    rollup_method = getattr(kpi, "auto_expand_accounts_rollup", "sum")
    if rollup_method != "sum":
        return
    detail_rows = self._detail_rows.get(kpi)
    if not detail_rows:
        return

    children = defaultdict(list)
    for acc_id, row in detail_rows.items():
        parent = row.parent_account_id
        if parent and parent in detail_rows:
            children[parent].append(acc_id)

    if not any(children.values()):
        return

    order = []
    visited = set()

    def _post_order(acc_id):
        if acc_id in visited:
            return
        visited.add(acc_id)
        for c in children[acc_id]:
            _post_order(c)
        order.append(acc_id)

    for acc_id in detail_rows:
        _post_order(acc_id)

    resolved_cols = [(k, c) for k, c in self._cols.items() if c is not None]

    for parent_id in order:
        if not children[parent_id]:
            continue
        parent_row = detail_rows[parent_id]
        for col_key, col in resolved_cols:
            parent_tuple = col.get_cell_tuple_for_row(parent_row)
            new_vals = []
            for i in range(col.colspan):
                own = AccountingNone
                if parent_tuple is not None and parent_tuple[i] is not None:
                    own = parent_tuple[i].val
                acc = own
                for child_id in children[parent_id]:
                    child_tuple = col.get_cell_tuple_for_row(detail_rows[child_id])
                    if child_tuple is None or child_tuple[i] is None:
                        continue
                    cval = child_tuple[i].val
                    if cval is AccountingNone or cval is None:
                        continue
                    acc = (cval if acc is AccountingNone else acc + cval)
                new_vals.append(acc)
            self.set_values_detail_account(
                kpi, col_key, parent_id, new_vals,
                [None] * col.colspan, tooltips=False,
            )


def _expand_and_rollup_all(self):
    """Apply hierarchical expansion + rollup to every KPI that opted in.

    Idempotent: subsequent calls are no-ops, so it is safe to call from
    multiple pre-hooks (compute_comparisons, compute_sums).
    """
    if getattr(self, "_hierarchy_expanded", False):
        return
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


_orig_compute_sums = KpiMatrix.compute_sums


def _patched_compute_sums(self):
    self._expand_and_rollup_all()
    _orig_compute_sums(self)


KpiMatrix.compute_sums = _patched_compute_sums


_orig_iter_rows = KpiMatrix.iter_rows


def _patched_iter_rows(self):
    """Depth-first iteration: KPI row, then its detail rows in tree order.

    For non-hierarchical KPIs, falls back to the original label-sorted flat order.
    """
    for kpi_row in self._kpi_rows.values():
        yield kpi_row
        detail_rows = self._detail_rows[kpi_row.kpi]
        if not detail_rows:
            continue
        if not _hierarchy_enabled(kpi_row.kpi):
            for row in sorted(detail_rows.values(), key=lambda r: r.label):
                yield row
            continue
        children = defaultdict(list)
        for acc_id, row in detail_rows.items():
            parent = row.parent_account_id
            if parent and parent in detail_rows:
                children[parent].append(acc_id)
        roots = [
            acc_id for acc_id, row in detail_rows.items()
            if not row.parent_account_id or row.parent_account_id not in detail_rows
        ]
        visited = set()

        def _walk(acc_id):
            if acc_id in visited:
                return
            visited.add(acc_id)
            row = detail_rows[acc_id]
            yield row
            for child_id in sorted(children[acc_id], key=lambda i: detail_rows[i].label):
                yield from _walk(child_id)

        for root_id in sorted(roots, key=lambda i: detail_rows[i].label):
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
    children_by_parent = defaultdict(set)
    for r in visible_rows:
        if r.account_id and getattr(r, "parent_account_id", None):
            children_by_parent[(r.kpi.id, r.parent_account_id)].add(r.account_id)
    for row_data, row in zip(visible_rows, result["body"]):
        kpi = row.kpi
        hierarchical = _hierarchy_enabled(kpi) and row.account_id is not None
        row_data["level"] = getattr(row, "level", 0)
        row_data["kpi_id"] = kpi.id
        row_data["account_id"] = row.account_id
        row_data["parent_account_id"] = getattr(row, "parent_account_id", None)
        if hierarchical:
            row_data["row_key"] = "{}#{}".format(kpi.id, row.account_id)
            parent_acc = row.parent_account_id
            row_data["parent_row_key"] = (
                "{}#{}".format(kpi.id, parent_acc) if parent_acc else None
            )
            row_data["has_children"] = bool(
                children_by_parent.get((kpi.id, row.account_id))
            )
        else:
            row_data["row_key"] = None
            row_data["parent_row_key"] = None
            row_data["has_children"] = False
    return result


KpiMatrix.as_dict = _patched_as_dict
