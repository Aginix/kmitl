/** @odoo-module **/

export const CHART_COLORS = [
    "#5470c6",
    "#91cc75",
    "#fac858",
    "#ee6666",
    "#73c0de",
    "#3ba272",
    "#fc8452",
    "#9a60b4",
    "#ea7ccc",
    "#48b8d0",
];

export function formatCurrency(amount) {
    if (amount === null || amount === undefined) {
        return "0.00";
    }
    return new Intl.NumberFormat("th-TH", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(amount);
}

export function formatNumber(num) {
    if (num === null || num === undefined) {
        return "0";
    }
    return new Intl.NumberFormat("th-TH").format(num);
}

export function makeStackedBarOption(data, xData, xAxisOpts = {}) {
    const series = (data.series || []).map((s, i) => ({
        name: s.name,
        type: "bar",
        stack: "total",
        emphasis: {focus: "series"},
        data: s.data,
        itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
    }));

    return {
        tooltip: {
            trigger: "axis",
            axisPointer: {type: "shadow"},
            formatter: (params) => {
                let result = `<strong>${params[0].axisValue}</strong><br/>`;
                params.forEach((p) => {
                    if (p.value > 0) {
                        result += `${p.marker} ${p.seriesName}: ${formatCurrency(p.value)} บาท<br/>`;
                    }
                });
                return result;
            },
        },
        legend: {
            top: 0,
            type: "scroll",
        },
        grid: {
            left: "3%",
            right: "4%",
            bottom: "3%",
            top: 40,
            containLabel: true,
        },
        xAxis: {
            type: "category",
            data: xData,
            ...xAxisOpts,
        },
        yAxis: {
            type: "value",
            axisLabel: {
                formatter: (val) => {
                    if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
                    if (val >= 1e3) return `${(val / 1e3).toFixed(0)}K`;
                    return val;
                },
            },
        },
        series: series,
    };
}

export function makeStackedLineOption(data, xData) {
    const option = makeStackedBarOption(data, xData);
    option.xAxis.boundaryGap = false;
    option.series = (data.series || []).map((s, i) => ({
        name: s.name,
        type: "line",
        stack: "total",
        smooth: true,
        emphasis: {focus: "series"},
        data: s.data,
        itemStyle: {color: CHART_COLORS[i % CHART_COLORS.length]},
    }));
    return option;
}

export function makeDoughnutOption(seriesName, pieData) {
    return {
        tooltip: {
            trigger: "item",
            formatter: (params) =>
                `${params.name}: ${formatCurrency(params.value)} บาท (${params.percent.toFixed(1)}%)`,
        },
        legend: {
            orient: "vertical",
            right: "5%",
            top: "center",
        },
        series: [
            {
                name: seriesName,
                type: "pie",
                radius: ["40%", "70%"],
                center: ["35%", "50%"],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: "#fff",
                    borderWidth: 2,
                },
                label: {
                    show: true,
                    formatter: (params) =>
                        params.percent < 5
                            ? ""
                            : `${params.percent.toFixed(0)}%`,
                    position: "inside",
                    fontSize: 11,
                    fontWeight: "bold",
                    color: "#fff",
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: "rgba(0, 0, 0, 0.2)",
                    },
                },
                data: pieData,
            },
        ],
    };
}

// Build a purchase.request list-view domain from active dashboard filters plus a
// chart-specific tuple. Mirrors the backend filter logic so a click-through tree
// view shows the same records contributing to the chart slice.
export function pieDrilldownDomain(filters, selectedStates, extraFilter) {
    const domain = [
        extraFilter,
        ["account_fiscal_year_id", "=", filters.fiscal_year_id],
        ["source_analytic_id", "=", filters.source_id],
    ];
    if (selectedStates.length > 0) {
        domain.push(["state", "in", selectedStates]);
    } else {
        domain.push(["state", "not in", ["approved", "cancelled", "rejected"]]);
    }
    return domain;
}
