/** @odoo-module **/

import {dashboardChartRegistry} from "@purchase_request_dashboard/dashboard_registry";

function durationToColor(value, maxVal) {
    const ratio = Math.min(value / maxVal, 1);
    // ratio 0 = เขียว (#3ba272), ratio 1 = แดง (#ee6666)
    const r = Math.round(59 + (238 - 59) * ratio);
    const g = Math.round(162 + (102 - 162) * ratio);
    const b = Math.round(114 + (102 - 114) * ratio);
    return `rgb(${r},${g},${b})`;
}

function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes.toFixed(2)} นาที`;
    } else if (minutes < 60 * 24) {
        return `${(minutes / 60).toFixed(2)} ชั่วโมง`;
    }
    return `${(minutes / 60 / 24).toFixed(2)} วัน`;
}

function renderLeadtime(chart, data) {
    const raw = data || [];
    if (!raw.length) return;

    const maxVal = Math.max(...raw.map((d) => d.avg), 1);

    const treemapData = raw.map((item) => ({
        name: item.name,
        value: Math.max(item.avg, 0.1),
        itemStyle: {
            color:
                item.avg === 0
                    ? "#d9d9d9"
                    : durationToColor(item.avg, maxVal),
        },
        _avg: item.avg,
        _total: item.total,
        _count: item.count,
    }));

    chart.setOption(
        {
            tooltip: {
                formatter: (params) => {
                    const d = params.data;
                    if (d._avg === 0) {
                        return `<strong>${d.name}</strong><br/>ยังไม่มีข้อมูล`;
                    }
                    return `
                        <strong>${d.name}</strong><br/>
                        ระยะเวลาเฉลี่ย: ${formatDuration(d._avg)}<br/>
                        ระยะเวลาสะสม: ${formatDuration(d._total)}<br/>
                    `;
                },
            },
            series: [
                {
                    name: "Leadtime",
                    type: "treemap",
                    roam: false,
                    nodeClick: false,
                    breadcrumb: {show: false},
                    width: "100%",
                    height: "100%",
                    label: {
                        show: true,
                        formatter: (params) => {
                            const d = params.data;
                            if (d._avg === 0) {
                                return `{name|${d.name}}\n{sub|ยังไม่มีข้อมูล}`;
                            }
                            return `{name|${d.name}}\n{sub|${formatDuration(d._avg)}}`;
                        },
                        rich: {
                            name: {
                                fontSize: 13,
                                fontWeight: "bold",
                                color: "#fff",
                                lineHeight: 20,
                            },
                            sub: {
                                fontSize: 12,
                                color: "rgba(255,255,255,0.85)",
                                lineHeight: 18,
                            },
                        },
                    },
                    itemStyle: {
                        borderWidth: 4,
                        borderColor: "#fff",
                        gapWidth: 4,
                    },
                    data: treemapData,
                },
            ],
        },
        true
    );
}

dashboardChartRegistry.add("prChartLeadtime", {
    id: "prChartLeadtime",
    title: "leadtime",
    sequence: 70,
    endpoint: "/purchase_request/dashboard/leadtime_heatmap",
    render: renderLeadtime,
});
