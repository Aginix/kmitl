/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useEffect, useRef } from "@odoo/owl";

// Thin OWL wrapper over Apache ECharts (vendored at budget/static/lib/echarts).
// ECharts ships as a UMD bundle that attaches to ``window.echarts``; we init on
// mount, re-apply the option whenever it changes, follow viewport resizes, and
// dispose on unmount. The host element must have a non-zero height from CSS
// (ECharts measures it at init time).
export class EChart extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.chart = null;
        this._onResize = () => this.chart && this.chart.resize();
        onMounted(() => {
            this.chart = window.echarts.init(this.chartRef.el);
            this.chart.setOption(this.props.option || {});
            window.addEventListener("resize", this._onResize);
        });
        // Rebuild from scratch (notMerge=true) on each new option object so a
        // changed filter never leaves stale series/axes behind.
        useEffect(
            () => {
                if (this.chart) {
                    this.chart.setOption(this.props.option || {}, true);
                }
            },
            () => [this.props.option]
        );
        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            if (this.chart) {
                this.chart.dispose();
                this.chart = null;
            }
        });
    }
}

EChart.template = "budget.EChart";
EChart.props = {
    option: { type: Object, optional: true },
};
