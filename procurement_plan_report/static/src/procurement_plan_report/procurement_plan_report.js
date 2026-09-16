/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { MultiRecordSelect } from "./multi_record_select";

const REPORT_MODEL = "procurement.plan.report";

// Column spec — one flat table per group. The two equipment-only columns
// (ประเภทครุภัณฑ์, ราคาต่อหน่วย) drop out for construction.
function buildColumns(isEquipment) {
    const cols = [
        { key: "tag", label: _t("แผน/ผล"), cls: "text-center o_ppr_tag" },
        { key: "name", label: _t("รายการ") },
    ];
    if (isEquipment) {
        cols.push({ key: "category", label: _t("ประเภทครุภัณฑ์") });
    }
    cols.push({ key: "amount", label: _t("จำนวน"), cls: "text-end" });
    cols.push({ key: "unit", label: _t("หน่วยนับ"), cls: "text-center" });
    if (isEquipment) {
        cols.push({ key: "unit_price", label: _t("ราคาต่อหน่วย"), cls: "text-end", num: true });
    }
    cols.push({ key: "total", label: _t("วงเงินรวม"), cls: "text-end", num: true });
    cols.push({ key: "method", label: _t("วิธีการจัดซื้อจัดจ้าง") });
    cols.push({ key: "pr", label: _t("จัดทำ พ.1"), cls: "text-center" });
    cols.push({ key: "announce", label: _t("ประกาศ"), cls: "text-center" });
    cols.push({ key: "approve", label: _t("อนุมัติผล"), cls: "text-center" });
    cols.push({ key: "sign", label: _t("ลงนามสัญญา"), cls: "text-center" });
    cols.push({ key: "accept", label: _t("ตรวจรับ/ส่งมอบ"), cls: "text-center" });
    cols.push({ key: "inst_no", label: _t("งวด"), cls: "text-center" });
    cols.push({ key: "inst_days", label: _t("จำนวนวัน"), cls: "text-center" });
    cols.push({ key: "inst_month", label: _t("เดือน"), cls: "text-center" });
    cols.push({ key: "inst_amount", label: _t("จำนวนเงิน"), cls: "text-end", num: true });
    cols.push({ key: "note", label: _t("หมายเหตุ") });
    return cols;
}

export class ProcurementPlanReport extends Component {
    setup() {
        useSubEnv({ config: { ...getDefaultConfig(), ...this.env.config } });
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        const ctx = this.props.action.context || {};
        this.reportType = ctx.report_type || "construction";
        this.fiscalYears = [];
        this.state = useState({
            fiscalYearId: ctx.default_fiscal_year_id || false,
            departments: [],
            data: null,
            loading: false,
        });
        this.labels = { departments: _t("หน่วยงาน") };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.companyId = this.company.currentCompany.id;
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        if (!this.state.fiscalYearId) {
            const today = new Date().toISOString().slice(0, 10);
            const covering = this.fiscalYears.find(
                (fy) => fy.date_from <= today && fy.date_to >= today
            );
            const fy = covering || this.fiscalYears[0];
            this.state.fiscalYearId = fy ? fy.id : false;
        }
        // Pre-scope from a plan's smart button.
        const ctx = this.props.action.context || {};
        if (ctx.default_department_id) {
            const recs = await this.orm.read(
                "account.analytic.account",
                [ctx.default_department_id],
                ["display_name"]
            );
            if (recs.length) {
                this.state.departments = [
                    { id: recs[0].id, name: recs[0].display_name },
                ];
            }
        }
        await this.load();
    }

    get title() {
        return this.state.data ? this.state.data.title : "";
    }

    get columns() {
        const isEquip = this.state.data ? this.state.data.is_equipment : false;
        return buildColumns(isEquip);
    }

    get options() {
        return {
            company_id: this.companyId,
            report_type: this.reportType,
            fiscal_year_id: this.state.fiscalYearId,
            department_ids: this.state.departments.map((r) => r.id),
        };
    }

    async load() {
        if (!this.state.fiscalYearId) {
            this.state.data = null;
            return;
        }
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(REPORT_MODEL, "get_report_data", [
                this.options,
            ]);
        } finally {
            this.state.loading = false;
        }
    }

    onFiscalYearChange(ev) {
        this.state.fiscalYearId = parseInt(ev.target.value) || false;
        this.load();
    }

    onDepartmentChange(selected) {
        this.state.departments = selected;
        this.load();
    }

    // ------------------------------------------------------------------
    // Rendering helpers — flatten each item into แผน/ผล + installment rows.
    // ------------------------------------------------------------------
    formatNumber(value) {
        if (value === null || value === undefined || value === "") {
            return "";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    cellValue(col, cells) {
        const value = cells[col.key];
        if (value === undefined || value === null || value === "") {
            return "";
        }
        return col.num ? this.formatNumber(value) : value;
    }

    itemRows(item) {
        return [
            ...this._sideRows(item, "plan"),
            ...this._sideRows(item, "actual"),
        ];
    }

    _sideRows(item, side) {
        const isPlan = side === "plan";
        const actual = item.actual || {};
        const eta = (isPlan ? item.eta : actual.eta) || {};
        const insts = (isPlan ? item.installments : actual.installments) || [];
        const first = insts[0] || {};
        const lead = {
            cls: isPlan ? "o_ppr_plan" : "o_ppr_actual",
            cells: {
                tag: isPlan ? _t("แผน") : _t("ผล"),
                name: item.name,
                category: item.equipment_category,
                amount: item.amount,
                unit: item.unit,
                unit_price: isPlan ? item.unit_price : actual.unit_price,
                total: isPlan ? item.total_price : actual.total_price,
                method: item.procurement_method,
                pr: eta.pr,
                announce: eta.announce,
                approve: eta.approve,
                sign: eta.sign,
                accept: eta.accept,
                inst_no: first.number,
                inst_days: first.days,
                inst_month: first.month,
                inst_amount: first.amount,
                note: isPlan ? "" : actual.contract_no || actual.reason || "",
            },
        };
        const rows = [lead];
        for (const extra of insts.slice(1)) {
            rows.push({
                cls: "o_ppr_inst",
                cells: {
                    inst_no: extra.number,
                    inst_days: extra.days,
                    inst_month: extra.month,
                    inst_amount: extra.amount,
                },
            });
        }
        return rows;
    }

    async exportXlsx() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_xlsx", [
            this.options,
        ]);
        await this.action.doAction(action);
    }
}

ProcurementPlanReport.template = "procurement_plan_report.ProcurementPlanReport";
ProcurementPlanReport.components = { Layout, MultiRecordSelect };

registry.category("actions").add("procurement_plan_report_form", ProcurementPlanReport);
