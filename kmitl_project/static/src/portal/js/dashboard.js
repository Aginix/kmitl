/** @odoo-module **/

const { Component, useState, onMounted, onWillStart, mount, xml } = owl;

class ProjectDashboard extends Component {
    static template = xml`
        <div id="project_dashboard" class="container-fluid py-4">
            <!-- Header Row: Title -->
            <div class="row mb-4">
                <div class="col-12">
                    <h1 class="mb-0 dashboard-title">โครงการหน่วยงาน</h1>
                    <p class="text-muted mb-0">ภาพรวมโครงการ/กิจกรรม</p>
                </div>
            </div>

            <!-- Filter Row -->
            <div class="card filter-card mb-4">
                <div class="card-body py-3">
                    <div class="row g-3 align-items-end">
                        <!-- Fiscal Year Filter -->
                        <div class="col-md-6">
                            <label class="form-label small mb-1">ปีงบประมาณ</label>
                            <select class="form-select" t-on-change="onFiscalYearChange">
                                <t t-foreach="props.fiscalYears" t-as="fy" t-key="fy.id">
                                    <option t-att-value="fy.id"
                                            t-att-selected="isFiscalYearSelected(fy.id)">
                                        <t t-esc="fy.name"/>
                                    </option>
                                </t>
                            </select>
                        </div>

                        <!-- Department Filter -->
                        <div class="col-md-6">
                            <label class="form-label small mb-1">หน่วยงาน</label>
                            <select class="form-select" t-on-change="onDepartmentChange">
                                <option value="">ทั้งหมด</option>
                                <t t-foreach="props.departments" t-as="dept" t-key="dept.id">
                                    <option t-att-value="dept.id"
                                            t-att-selected="isDepartmentSelected(dept.id)">
                                        [<t t-esc="dept.code"/>] <t t-esc="dept.name"/>
                                    </option>
                                </t>
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Statistics Cards Row -->
            <div class="row mb-4 g-3">
                <!-- Total Projects Card -->
                <div class="col">
                    <div class="card stat-card h-100">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle text-muted mb-2">จำนวนโครงการทั้งหมด</h6>
                            <h2 class="stat-number text-primary">
                                <t t-if="state.loading">
                                    <span class="placeholder-glow"><span class="placeholder col-4"></span></span>
                                </t>
                                <t t-elif="state.error">-</t>
                                <t t-else="" t-esc="state.stats.total"/>
                            </h2>
                        </div>
                    </div>
                </div>

                <!-- Education Impact Card -->
                <div class="col">
                    <div class="card stat-card h-100">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle text-muted mb-2">Education</h6>
                            <h2 class="stat-number text-info">
                                <t t-if="state.loading">
                                    <span class="placeholder-glow"><span class="placeholder col-4"></span></span>
                                </t>
                                <t t-elif="state.error">-</t>
                                <t t-else="" t-esc="state.stats.education"/>
                            </h2>
                        </div>
                    </div>
                </div>

                <!-- Academic Impact Card -->
                <div class="col">
                    <div class="card stat-card h-100">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle text-muted mb-2">Academic</h6>
                            <h2 class="stat-number text-success">
                                <t t-if="state.loading">
                                    <span class="placeholder-glow"><span class="placeholder col-4"></span></span>
                                </t>
                                <t t-elif="state.error">-</t>
                                <t t-else="" t-esc="state.stats.academic"/>
                            </h2>
                        </div>
                    </div>
                </div>

                <!-- Industrial Impact Card -->
                <div class="col">
                    <div class="card stat-card h-100">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle text-muted mb-2">Industrial</h6>
                            <h2 class="stat-number text-warning">
                                <t t-if="state.loading">
                                    <span class="placeholder-glow"><span class="placeholder col-4"></span></span>
                                </t>
                                <t t-elif="state.error">-</t>
                                <t t-else="" t-esc="state.stats.industrial"/>
                            </h2>
                        </div>
                    </div>
                </div>

                <!-- Social Impact Card -->
                <div class="col">
                    <div class="card stat-card h-100">
                        <div class="card-body text-center">
                            <h6 class="card-subtitle text-muted mb-2">Social</h6>
                            <h2 class="stat-number text-danger">
                                <t t-if="state.loading">
                                    <span class="placeholder-glow"><span class="placeholder col-4"></span></span>
                                </t>
                                <t t-elif="state.error">-</t>
                                <t t-else="" t-esc="state.stats.social"/>
                            </h2>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Pie Chart Row -->
            <div class="row mb-4">
                <div class="col-md-8 mx-auto">
                    <div class="card">
                        <div class="card-header">
                            งบประมาณตาม Impact
                        </div>
                        <div class="card-body">
                            <div id="budgetPieChart" style="height: 400px;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Department Budget Table -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            สรุปงบประมาณตามหน่วยงาน
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-bordered table-hover mb-0 budget-table">
                                    <thead class="table-light">
                                        <tr>
                                            <th rowspan="2" class="align-middle text-center" style="min-width: 200px;">หน่วยงาน</th>
                                            <th colspan="3" class="text-center">งบประมาณที่ได้รับ</th>
                                            <th colspan="4" class="text-center">งบประมาณที่ใช้จริง</th>
                                            <th rowspan="2" class="align-middle text-center">งบประมาณทั้งหมด</th>
                                        </tr>
                                        <tr>
                                            <th class="text-center">เงินแผ่นดิน</th>
                                            <th class="text-center">เงินรายได้</th>
                                            <th class="text-center">อื่น ๆ</th>
                                            <th class="text-center">ไตรมาส 1</th>
                                            <th class="text-center">ไตรมาส 2</th>
                                            <th class="text-center">ไตรมาส 3</th>
                                            <th class="text-center">ไตรมาส 4</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-if="state.loading">
                                            <tr>
                                                <td colspan="9" class="text-center py-4">
                                                    <div class="spinner-border text-primary" role="status">
                                                        <span class="visually-hidden">Loading...</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </t>
                                        <t t-elif="state.error">
                                            <tr>
                                                <td colspan="9" class="text-center py-4 text-danger">
                                                    เกิดข้อผิดพลาดในการโหลดข้อมูล
                                                </td>
                                            </tr>
                                        </t>
                                        <t t-elif="!state.tableData.length">
                                            <tr>
                                                <td colspan="9" class="text-center py-4 text-muted">
                                                    ไม่มีข้อมูล
                                                </td>
                                            </tr>
                                        </t>
                                        <t t-else="">
                                            <t t-foreach="state.tableData" t-as="row" t-key="row.department_code">
                                                <tr>
                                                    <td>[<t t-esc="row.department_code"/>] <t t-esc="row.department_name"/></td>
                                                    <td class="text-end"><t t-esc="formatNumber(row.budget_source_1)"/></td>
                                                    <td class="text-end"><t t-esc="formatNumber(row.budget_source_2)"/></td>
                                                    <td class="text-end"><t t-esc="formatNumber(row.budget_other)"/></td>
                                                    <td class="text-center text-muted"><t t-esc="row.q1"/></td>
                                                    <td class="text-center text-muted"><t t-esc="row.q2"/></td>
                                                    <td class="text-center text-muted"><t t-esc="row.q3"/></td>
                                                    <td class="text-center text-muted"><t t-esc="row.q4"/></td>
                                                    <td class="text-end fw-bold"><t t-esc="formatNumber(row.total_budget)"/></td>
                                                </tr>
                                            </t>
                                        </t>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    setup() {
        this.state = useState({
            fiscalYearId: this.props.initialFiscalYearId || (this.props.fiscalYears[0]?.id || null),
            departmentId: this.props.initialDepartmentId || null,
            loading: true,
            error: false,
            stats: {
                total: 0,
                education: 0,
                academic: 0,
                industrial: 0,
                social: 0,
            },
            chartData: null,
            tableData: [],
        });

        this.chart = null;

        onWillStart(async () => {
            await this._loadECharts();
        });

        onMounted(() => {
            this._initFiltersFromUrl();
            this._loadDashboardData();
        });
    }

    async _loadECharts() {
        if (typeof echarts !== 'undefined') {
            return;
        }
        return new Promise((resolve) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
            script.onload = resolve;
            script.onerror = () => {
                console.error('Failed to load ECharts');
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    _initFiltersFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const urlFiscalYear = params.get('fiscal_year_id');
        const urlDepartment = params.get('department_id');

        if (urlFiscalYear) {
            this.state.fiscalYearId = urlFiscalYear;
        }
        if (urlDepartment) {
            this.state.departmentId = urlDepartment;
        }

        this._updateUrl(false);
    }

    _updateUrl(pushState = true) {
        const params = new URLSearchParams();
        if (this.state.fiscalYearId) {
            params.set('fiscal_year_id', this.state.fiscalYearId);
        }
        if (this.state.departmentId) {
            params.set('department_id', this.state.departmentId);
        }
        const newUrl = '/project/dashboard?' + params.toString();
        if (pushState) {
            history.pushState(null, '', newUrl);
        } else {
            history.replaceState(null, '', newUrl);
        }
    }

    onFiscalYearChange(ev) {
        this.state.fiscalYearId = ev.target.value || null;
        this._updateUrl();
        this._loadDashboardData();
    }

    onDepartmentChange(ev) {
        this.state.departmentId = ev.target.value || null;
        this._updateUrl();
        this._loadDashboardData();
    }

    async _loadDashboardData() {
        this.state.loading = true;
        this.state.error = false;

        try {
            const response = await fetch('/project/dashboard/api', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        fiscal_year_id: this.state.fiscalYearId,
                        department_id: this.state.departmentId,
                    },
                    id: Date.now(),
                }),
            });

            const result = await response.json();

            if (result.result) {
                this.state.stats = result.result.impact_stats;
                this.state.chartData = result.result.chart_data;
                this.state.tableData = result.result.department_budget_table || [];
                this.state.loading = false;

                // Update chart after DOM update
                setTimeout(() => this._updateChart(), 100);
            } else {
                throw new Error(result.error || 'API Error');
            }
        } catch (error) {
            console.error('API Error:', error);
            this.state.error = true;
            this.state.loading = false;
        }
    }

    _updateChart() {
        if (typeof echarts === 'undefined' || !this.state.chartData?.budget_by_impact) {
            return;
        }

        const chartDom = document.getElementById('budgetPieChart');
        if (!chartDom) {
            return;
        }

        if (!this.chart) {
            this.chart = echarts.init(chartDom);
            window.addEventListener('resize', () => {
                if (this.chart) {
                    this.chart.resize();
                }
            });
        }

        const impactColors = {
            'Education': '#17a2b8',
            'Academic': '#28a745',
            'Industrial': '#ffc107',
            'Social': '#dc3545',
        };

        const pieData = this.state.chartData.budget_by_impact.map((item) => ({
            name: item.name,
            value: item.value,
            itemStyle: {
                color: impactColors[item.name] || '#6c757d'
            }
        }));

        const option = {
            title: {
                text: '',
                left: 'center'
            },
            tooltip: {
                trigger: 'item',
                formatter: (params) => {
                    const value = params.value.toLocaleString('th-TH');
                    return `${params.name}: ${value} บาท (${params.percent.toFixed(1)}%)`;
                }
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                top: 'middle'
            },
            series: [
                {
                    name: 'งบประมาณ',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    center: ['60%', '50%'],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 10,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        show: true,
                        formatter: (params) => `${params.name}\n${params.percent.toFixed(1)}%`
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 16,
                            fontWeight: 'bold'
                        },
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    },
                    labelLine: {
                        show: true
                    },
                    data: pieData
                }
            ]
        };

        this.chart.setOption(option, true);
    }

    formatNumber(num) {
        if (num === null || num === undefined) {
            return '0.00';
        }
        return num.toLocaleString('th-TH', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    isFiscalYearSelected(fyId) {
        return String(fyId) === String(this.state.fiscalYearId);
    }

    isDepartmentSelected(deptId) {
        return String(deptId) === String(this.state.departmentId);
    }
}

// Mount function for portal
function mountProjectDashboard() {
    const container = document.getElementById('project_dashboard_owl');
    if (!container) {
        return;
    }

    // Get props from data attributes
    const fiscalYearsData = container.dataset.fiscalYears;
    const departmentsData = container.dataset.departments;
    const initialFiscalYearId = container.dataset.initialFiscalYearId || null;
    const initialDepartmentId = container.dataset.initialDepartmentId || null;

    const fiscalYears = fiscalYearsData ? JSON.parse(fiscalYearsData) : [];
    const departments = departmentsData ? JSON.parse(departmentsData) : [];

    mount(ProjectDashboard, container, {
        props: {
            fiscalYears,
            departments,
            initialFiscalYearId,
            initialDepartmentId,
        },
    });
}

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountProjectDashboard);
} else {
    mountProjectDashboard();
}
