/** @odoo-module **/

import {dashboardChartRegistry} from "@purchase_request_dashboard/dashboard_registry";
import {
    CHART_COLORS,
    makeDoughnutOption,
    makeStackedBarOption,
    pieDrilldownDomain,
} from "@purchase_request_dashboard/utils";

const DEPT_AXIS_OPTS = {
    axisLabel: {rotate: 30, overflow: "truncate", width: 80},
};

function renderExpenseTypePie(chart, data, ctx) {
    const pieData = (data || []).map((item, i) => ({
        ...item,
        itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
    }));
    chart.setOption(makeDoughnutOption("ประเภทค่าใช้จ่าย", pieData), true);

    chart.off("click");
    chart.on("click", (params) => {
        const ids = params.data.budget_account_ids;
        if (!ids || !ids.length) return;
        ctx.action.doAction({
            type: "ir.actions.act_window",
            name: params.name,
            res_model: "purchase.request",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: pieDrilldownDomain(ctx.filters, ctx.selectedStates, [
                "budget_account_id",
                "in",
                ids,
            ]),
            target: "current",
        });
    });
}

function renderExpenseByMonth(chart, data) {
    chart.setOption(makeStackedBarOption(data, data.months || []), true);
}

function renderExpenseByDept(chart, data) {
    chart.setOption(
        makeStackedBarOption(data, data.departments || [], DEPT_AXIS_OPTS),
        true
    );
}

dashboardChartRegistry.add("prChartExpPie", {
    id: "prChartExpPie",
    title: "ประเภทค่าใช้จ่าย",
    sequence: 25,
    endpoint: "/purchase_request/dashboard/expense_type_pie",
    render: renderExpenseTypePie,
});

dashboardChartRegistry.add("prChart3", {
    id: "prChart3",
    title: "ประเภทค่าใช้จ่าย (รายเดือน)",
    sequence: 30,
    endpoint: "/purchase_request/dashboard/expense_by_month",
    render: renderExpenseByMonth,
});

dashboardChartRegistry.add("prChart6", {
    id: "prChart6",
    title: "ประเภทค่าใช้จ่าย (ตามส่วนงาน)",
    sequence: 60,
    endpoint: "/purchase_request/dashboard/expense_by_dept",
    render: renderExpenseByDept,
});
