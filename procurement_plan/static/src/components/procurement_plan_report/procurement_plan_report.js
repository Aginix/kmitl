/** @odoo-module */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {registry} from "@web/core/registry";

export class ProcurementPlanReport extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            selected_year: "ทั้งหมด",
            selected_department: "ทั้งหมด",
            selected_source: "ทั้งหมด",
            loading: false,
            error: null,
            filters: {
                fiscal_year_id: null,
                department_analytic_id: null,
                department_ids: [],
                source_analytic_id: null,
            },
            filterOptions: {
                fiscal_years: [],
                departments: [],
                sources: [],
                departments_flat: [],
                states: [],
            },
            record: [],
        });

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadData();
        });
    }

    async loadFilterOptions() {
        try {
            const options = await this.orm.call(
                "procurement.plan",
                "get_filter_options",
                []
            );
            this.state.filterOptions = options;
        } catch (error) {
            this.state.error = "ไม่สามารถโหลดตัวเลือกการกรองได้";
        }
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        console.log("Selected Source:", this.state.filters);
        try {
            const data = await this.orm.call(
                "procurement.plan",
                "get_procurement_plan_data",
                [this.state.filters]
            );
            this.state.record = data.records || [];
        } catch (error) {
            this.state.error = "เกิดข้อผิดพลาดในการโหลดข้อมูล";
        } finally {
            this.state.loading = false;
        }
    }

    // Event handlers
    async onFilterChange() {
        await this.loadData();
    }

    async onFiscalYearChange(ev) {
        const fiscalYearId = parseInt(ev.target.value) || null;
        this.state.filters.fiscal_year_id = fiscalYearId;


        const fiscalYear = this.state.filterOptions.fiscal_years.find(
            (fy) => fy.id === fiscalYearId
        );
        if (fiscalYear) {
            this.state.selected_year = fiscalYear.name;
            this.state.filters.date_from = fiscalYear.date_start;
            this.state.filters.date_to = fiscalYear.date_end;
        }

        await this.onFilterChange();
    }

    async onDepartmentChange(ev) {
        const deptId = parseInt(ev.target.value) || null;
        this.state.filters.department_analytic_id = deptId;
        const departmentAnalytic = this.state.filterOptions.departments.find(
            (fy) => fy.id === deptId
        );
        this.state.selected_department = departmentAnalytic.name;
        await this.onFilterChange();
    }

    async onSourceChange(ev) {
        const sourceId = parseInt(ev.target.value) || null;
        this.state.filters.source_analytic_id = sourceId;
        const sourceAnalytic = this.state.filterOptions.sources.find(
            (fy) => fy.id === sourceId
        );
        this.state.selected_source = sourceAnalytic.name;
        await this.onFilterChange();
    }

    getThaiMonthName(monthNumber) {
        const thaiMonths = [
            "",
            "มกราคม",
            "กุมภาพันธ์",
            "มีนาคม",
            "เมษายน",
            "พฤษภาคม",
            "มิถุนายน",
            "กรกฎาคม",
            "สิงหาคม",
            "กันยายน",
            "ตุลาคม",
            "พฤศจิกายน",
            "ธันวาคม",
        ];
        const num = parseInt(monthNumber);
        return thaiMonths[num] || "-";
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat("th-TH", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    }
}

ProcurementPlanReport.template = "procurement_plan.ProcurementPlanReport";
ProcurementPlanReport.components = {
    Dropdown,
    DropdownItem,
};

registry.category("actions").add("procurement_plan_report", ProcurementPlanReport);
