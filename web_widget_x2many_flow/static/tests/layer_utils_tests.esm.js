/** @odoo-module **/

import {
    buildLayers,
    planDrop,
    resolveLayerKey,
} from "@web_widget_x2many_flow/x2many_flow/layer_utils.esm";

/* global QUnit */

const rec = (id, order) => ({id, data: {order}});
const plan = (records, movedId, target, locked = []) =>
    planDrop(buildLayers(records, "order"), movedId, target, (r) =>
        locked.includes(r.id)
    );
const values = (result) =>
    Object.fromEntries(result.updates.map(({record, value}) => [record.id, value]));

QUnit.module("web_widget_x2many_flow", {}, () => {
    QUnit.module("layer_utils");

    QUnit.test("resolveLayerKey: option, handle, sequence, order", (assert) => {
        const fields = {
            sequence: {type: "integer"},
            order: {type: "integer"},
            name: {type: "char"},
            weight: {type: "float"},
        };
        const archInfo = {
            activeFields: {sequence: {}, order: {}, name: {}, weight: {}},
        };
        assert.deepEqual(resolveLayerKey(archInfo, fields, "weight"), {name: "weight"});
        assert.deepEqual(resolveLayerKey({...archInfo, handleField: "order"}, fields), {
            name: "order",
        });
        assert.deepEqual(resolveLayerKey(archInfo, fields), {name: "sequence"});
        assert.strictEqual(
            resolveLayerKey(archInfo, fields, "name").error,
            "not_numeric"
        );
        assert.strictEqual(resolveLayerKey(archInfo, fields, "nope").error, "no_field");
        assert.strictEqual(
            resolveLayerKey({activeFields: {}}, fields, "order").error,
            "not_in_tree"
        );
    });

    QUnit.test("buildLayers groups equal keys, sorted ascending", (assert) => {
        const layers = buildLayers([rec("a", 3), rec("b", 1), rec("c", 3)], "order");
        assert.deepEqual(
            layers.map((l) => [l.value, l.records.map((r) => r.id)]),
            [
                [1, ["b"]],
                [3, ["a", "c"]],
            ]
        );
    });

    QUnit.test("join a layer", (assert) => {
        const records = [rec("a", 1), rec("b", 2), rec("c", 3)];
        assert.deepEqual(values(plan(records, "c", {layer: 2})), {c: 2});
        assert.deepEqual(values(plan(records, "b", {layer: 2})), {});
    });

    QUnit.test("new layer in a gap with room", (assert) => {
        const records = [rec("a", 1), rec("b", 5), rec("c", 6)];
        // Gap 1 = between layer 1 and layer 5
        assert.deepEqual(values(plan(records, "c", {gap: 1})), {c: 2});
    });

    QUnit.test("new layer without room shifts only later layers", (assert) => {
        const records = [rec("a", 1), rec("b", 2), rec("c", 2), rec("d", 3)];
        // Drop d between layer 1 and layer 2: b, c move to 3
        assert.deepEqual(values(plan(records, "d", {gap: 1})), {d: 2, b: 3, c: 3});
    });

    QUnit.test("before the first / after the last layer", (assert) => {
        const records = [rec("a", 1), rec("b", 2), rec("c", 2)];
        assert.deepEqual(values(plan(records, "c", {gap: 0})), {c: 0});
        assert.deepEqual(values(plan(records, "a", {gap: 2})), {a: 3});
    });

    QUnit.test("dropping a lone node next to its own layer is a no-op", (assert) => {
        const records = [rec("a", 1), rec("b", 2), rec("c", 3)];
        assert.deepEqual(values(plan(records, "b", {gap: 1})), {});
        assert.deepEqual(values(plan(records, "b", {gap: 2})), {});
    });

    QUnit.test("locked nodes refuse being moved or pushed", (assert) => {
        const records = [rec("o", 1), rec("a", 2), rec("b", 3)];
        assert.strictEqual(plan(records, "o", {gap: 3}, ["o"]).error, "locked");
        // Inserting c between 2 and 3 without room would push locked b
        assert.strictEqual(
            plan([rec("o", 1), rec("a", 2), rec("b", 3), rec("c", 4)], "c", {gap: 2}, [
                "b",
            ]).error,
            "locked"
        );
        // A locked first layer keeps its place
        assert.strictEqual(plan(records, "b", {gap: 0}, ["o"]).error, "locked");
        assert.deepEqual(values(plan(records, "b", {gap: 1}, ["o"])), {b: 2, a: 3});
    });
});
