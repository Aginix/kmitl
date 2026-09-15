/** @odoo-module **/

import {registry} from "@web/core/registry";

/**
 * Registry for pluggable dashboard chart cards.
 *
 * Extension modules add entries at load time:
 *
 *   dashboardChartRegistry.add("prChart3", {
 *       id: "prChart3",
 *       title: "ประเภทค่าใช้จ่าย (รายเดือน)",
 *       sequence: 30,
 *       endpoint: "/purchase_request/dashboard/expense_by_month",
 *       render: (chartInstance, data, ctx) => { ... },
 *   });
 *
 * The core dashboard reads `getAll()` on render, sorts by sequence, and calls
 * each entry's `endpoint` with `{fiscal_year_id, source_id, selected_states}`.
 * The returned data is passed to `render(chartInstance, data, ctx)` where `ctx`
 * exposes `{filters, selectedStates, action}` for optional drill-through.
 */
export const dashboardChartRegistry = registry.category(
    "purchase_request_dashboard.chart_cards"
);

/**
 * Registry for summary box state colors.
 *
 * Extensions that add new PR states register their Bootstrap text-color class:
 *
 *   dashboardBoxColorRegistry.add("in_egp", "text-warning");
 *
 * The core component merges these with its built-in color map when rendering
 * each summary box.
 */
export const dashboardBoxColorRegistry = registry.category(
    "purchase_request_dashboard.box_colors"
);
