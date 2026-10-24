/** @odoo-module **/

/**
 * Pure Layer logic of the `x2many_flow` widget — no OWL, no ORM, so it is unit
 * tested on its own (static/tests/layer_utils_tests.esm.js).
 *
 * A Layer is the set of rows sharing one Layer Key value. Records only need an
 * `id` and a `data` object, which is exactly what a StaticList record exposes.
 */

const NUMERIC_TYPES = ["integer", "float"];

/**
 * Pick the Layer Key: `options.order_field`, else the tree's handle field, else
 * `sequence`, else `order`. It must be numeric and loaded by the sub tree, since
 * the widget reads its value and readonly modifier from the line records.
 *
 * @param {Object} archInfo sub tree arch info (handleField, activeFields)
 * @param {Object} fields fields of the line model
 * @param {String} [orderField] explicit `order_field` option
 * @returns {{name: String}|{error: String}}
 */
export function resolveLayerKey(archInfo, fields, orderField) {
    const candidates = orderField
        ? [orderField]
        : [archInfo.handleField, "sequence", "order"].filter(Boolean);
    const name = candidates.find((candidate) => candidate in fields);
    if (!name) {
        return {error: "no_field", name: orderField || "sequence / order"};
    }
    if (!NUMERIC_TYPES.includes(fields[name].type)) {
        return {error: "not_numeric", name};
    }
    if (!(name in (archInfo.activeFields || {}))) {
        return {error: "not_in_tree", name};
    }
    return {name};
}

/**
 * Group records into Layers sorted by ascending key; records keep their list
 * order inside a Layer.
 *
 * @param {Array} records
 * @param {String} key
 * @returns {Array<{value: Number, records: Array}>}
 */
export function buildLayers(records, key) {
    const byValue = new Map();
    for (const record of records) {
        const value = Number(record.data[key]) || 0;
        if (!byValue.has(value)) {
            byValue.set(value, []);
        }
        byValue.get(value).push(record);
    }
    return [...byValue.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([value, layerRecords]) => ({value, records: layerRecords}));
}

/**
 * An Anchored Layer is a first Layer holding a Locked Node (e.g. e-Saraban's
 * originator): nothing may join it, be added to it or be placed before it.
 *
 * @param {Array} layers as rendered, from buildLayers
 * @param {Number} index position of the Layer
 * @param {Function} isLocked record => Boolean
 * @param {String} [ignoreId] record left out of the check (the one being moved)
 * @returns {Boolean}
 */
export function isAnchoredLayer(layers, index, isLocked, ignoreId) {
    return (
        index === 0 &&
        layers.length > 0 &&
        layers[0].records.some((r) => r.id !== ignoreId && isLocked(r))
    );
}

/**
 * The New Layer half of planDrop: `moved` (out of `origin`) dropped in the gap
 * before `layers[gap]`.
 *
 * @param {Array} layers as rendered, from buildLayers
 * @param {Object} origin the Layer `moved` comes from
 * @param {Object} moved the dropped record
 * @param {Number} gap gap index
 * @param {Function} isLocked record => Boolean
 * @returns {Object} `{updates: [{record, value}]}` or `{error}`
 */
function planNewLayer(layers, origin, moved, gap, isLocked) {
    // The Layers left once the moved node is lifted out.
    const others = (layer) => layer.records.filter((r) => r.id !== moved.id);
    const before = layers.slice(0, gap).filter((layer) => others(layer).length);
    const after = layers.slice(gap).filter((layer) => others(layer).length);
    const lo = before.length ? before[before.length - 1].value : null;
    const hi = after.length ? after[0].value : null;

    // Dropped right next to its own single-node Layer: nothing changes.
    if (
        origin.records.length === 1 &&
        (lo === null || origin.value > lo) &&
        (hi === null || origin.value < hi)
    ) {
        return {updates: []};
    }
    if (hi === null) {
        return {updates: [{record: moved, value: lo + 1}]};
    }
    if (lo === null) {
        // Nothing is written to the first Layer, but it stops being first.
        if (isAnchoredLayer(after, 0, isLocked, moved.id)) {
            return {error: "anchored"};
        }
        return {updates: [{record: moved, value: hi - 1}]};
    }
    if (hi - lo >= 2) {
        return {updates: [{record: moved, value: lo + 1}]};
    }
    const shifted = after.flatMap((layer) =>
        others(layer).map((record) => ({record, value: layer.value + 1}))
    );
    if (shifted.some(({record}) => isLocked(record))) {
        return {error: "shift_locked"};
    }
    return {updates: [{record: moved, value: lo + 1}, ...shifted]};
}

/**
 * Compute the Layer Key writes for dropping `movedId` on a target (Minimal Shift,
 * see docs/adr/0001-minimal-shift-layer-reorder.md):
 *
 * - `{layer: value}` — Join: the node takes that Layer's value.
 * - `{gap: index}` — New Layer in the gap before `layers[index]` (`index ===
 *   layers.length` = after the last). A free value in the gap is used as is;
 *   otherwise only the Layers after the gap move up by one. Before the first
 *   Layer is first - 1, after the last is last + 1. Earlier Layers never move.
 *
 * Refused with `{error}`: "locked" when the moved node is locked, "shift_locked"
 * when a shift would move a locked node, "anchored" when it would join or land
 * before an Anchored Layer (isAnchoredLayer).
 *
 * @param {Array} layers as rendered, from buildLayers
 * @param {String} movedId
 * @param {Object} target `{layer: value}` or `{gap: index}`
 * @param {Function} isLocked record => Boolean
 * @returns {Object} `{updates: [{record, value}]}` or `{error}`
 */
export function planDrop(layers, movedId, target, isLocked) {
    const origin = layers.find((layer) => layer.records.some((r) => r.id === movedId));
    if (!origin) {
        return {updates: []};
    }
    const moved = origin.records.find((r) => r.id === movedId);
    if (isLocked(moved)) {
        return {error: "locked"};
    }
    if ("layer" in target) {
        if (target.layer === origin.value) {
            return {updates: []};
        }
        const index = layers.findIndex((layer) => layer.value === target.layer);
        if (isAnchoredLayer(layers, index, isLocked, movedId)) {
            return {error: "anchored"};
        }
        return {updates: [{record: moved, value: target.layer}]};
    }
    return planNewLayer(layers, origin, moved, target.gap, isLocked);
}
