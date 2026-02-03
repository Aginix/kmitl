odoo.define('kmitl_project.portal_dashboard', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    var DashboardWidget = publicWidget.Widget.extend({
        selector: '#project_dashboard',
        events: {
            'change #fiscal_year_filter': '_onFilterChange',
            'change #department_filter': '_onFilterChange',
        },

        start: function () {
            var self = this;
            this.dashboardChart = null;
            this.echartsLoaded = false;

            // Initialize filters from URL
            this._initFiltersFromUrl();

            // Load ECharts from CDN then load data
            this._loadECharts().then(function () {
                self.echartsLoaded = true;
                self._loadDashboardData();
            });

            return this._super.apply(this, arguments);
        },

        _loadECharts: function () {
            var self = this;
            return new Promise(function (resolve) {
                if (typeof echarts !== 'undefined') {
                    resolve();
                    return;
                }
                var script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
                script.onload = function () {
                    resolve();
                };
                script.onerror = function () {
                    console.error('Failed to load ECharts');
                    resolve(); // Continue anyway
                };
                document.head.appendChild(script);
            });
        },

        _initFiltersFromUrl: function () {
            var params = new URLSearchParams(window.location.search);
            var fiscalYearFilter = this.$('#fiscal_year_filter');
            var departmentFilter = this.$('#department_filter');

            // Sync URL with current filter state
            var needsUpdate = false;
            var newParams = new URLSearchParams();

            if (fiscalYearFilter.length && fiscalYearFilter.val()) {
                var urlFiscalYear = params.get('fiscal_year_id');
                if (urlFiscalYear !== fiscalYearFilter.val()) {
                    needsUpdate = true;
                }
                newParams.set('fiscal_year_id', fiscalYearFilter.val());
            }

            if (departmentFilter.length && departmentFilter.val()) {
                newParams.set('department_id', departmentFilter.val());
            }

            // Update URL without reload
            if (needsUpdate || (fiscalYearFilter.length && fiscalYearFilter.val() && !params.has('fiscal_year_id'))) {
                var newUrl = '/project/dashboard?' + newParams.toString();
                history.replaceState(null, '', newUrl);
            }
        },

        _onFilterChange: function () {
            this._updateUrl();
            this._loadDashboardData();
        },

        _updateUrl: function () {
            var params = new URLSearchParams();
            var fiscalYear = this.$('#fiscal_year_filter').val();
            var department = this.$('#department_filter').val();

            if (fiscalYear) {
                params.set('fiscal_year_id', fiscalYear);
            }
            if (department) {
                params.set('department_id', department);
            }

            var newUrl = '/project/dashboard?' + params.toString();
            history.pushState(null, '', newUrl);
        },

        _loadDashboardData: function () {
            var self = this;
            var fiscalYearId = this.$('#fiscal_year_filter').val() || null;
            var departmentId = this.$('#department_filter').val() || null;

            this._showLoadingState();

            ajax.jsonRpc('/project/dashboard/api', 'call', {
                fiscal_year_id: fiscalYearId,
                department_id: departmentId,
            }).then(function (data) {
                self._updateDashboard(data);
            }).guardedCatch(function (error) {
                console.error('API Error:', error);
                self._showErrorState();
            });
        },

        _showLoadingState: function () {
            var statIds = ['stat-total', 'stat-education', 'stat-academic', 'stat-industrial', 'stat-social'];
            var self = this;
            statIds.forEach(function (id) {
                var el = self.$('#' + id);
                if (el.length) {
                    el.html('<span class="placeholder-glow"><span class="placeholder col-4"></span></span>');
                }
            });

            var tableBody = this.$('#budget-table-body');
            if (tableBody.length) {
                tableBody.html('<tr><td colspan="9" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>');
            }
        },

        _showErrorState: function () {
            var statIds = ['stat-total', 'stat-education', 'stat-academic', 'stat-industrial', 'stat-social'];
            var self = this;
            statIds.forEach(function (id) {
                var el = self.$('#' + id);
                if (el.length) {
                    el.text('-');
                }
            });

            var tableBody = this.$('#budget-table-body');
            if (tableBody.length) {
                tableBody.html('<tr><td colspan="9" class="text-center py-4 text-danger">เกิดข้อผิดพลาดในการโหลดข้อมูล</td></tr>');
            }
        },

        _updateDashboard: function (data) {
            this._updateStats(data.impact_stats);
            this._updateChart(data.chart_data);
            this._updateTable(data.department_budget_table);
        },

        _updateStats: function (stats) {
            this.$('#stat-total').text(stats.total || 0);
            this.$('#stat-education').text(stats.education || 0);
            this.$('#stat-academic').text(stats.academic || 0);
            this.$('#stat-industrial').text(stats.industrial || 0);
            this.$('#stat-social').text(stats.social || 0);
        },

        _updateChart: function (chartData) {
            if (typeof echarts === 'undefined' || !chartData || !chartData.budget_by_impact) {
                return;
            }

            var chartDom = this.$('#budgetPieChart')[0];
            if (!chartDom) {
                return;
            }

            // Initialize or get existing chart
            if (!this.dashboardChart) {
                this.dashboardChart = echarts.init(chartDom);

                // Handle window resize
                var self = this;
                $(window).on('resize', function () {
                    if (self.dashboardChart) {
                        self.dashboardChart.resize();
                    }
                });
            }

            // Define colors for each Impact category
            var impactColors = {
                'Education': '#17a2b8',
                'Academic': '#28a745',
                'Industrial': '#ffc107',
                'Social': '#dc3545',
            };

            // Assign colors to data
            var pieData = chartData.budget_by_impact.map(function (item) {
                return {
                    name: item.name,
                    value: item.value,
                    itemStyle: {
                        color: impactColors[item.name] || '#6c757d'
                    }
                };
            });

            var option = {
                title: {
                    text: '',
                    left: 'center'
                },
                tooltip: {
                    trigger: 'item',
                    formatter: function (params) {
                        var value = params.value.toLocaleString('th-TH');
                        return params.name + ': ' + value + ' บาท (' + params.percent.toFixed(1) + '%)';
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
                            formatter: function (params) {
                                return params.name + '\n' + params.percent.toFixed(1) + '%';
                            }
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

            this.dashboardChart.setOption(option, true);
        },

        _updateTable: function (tableData) {
            var tableBody = this.$('#budget-table-body');
            if (!tableBody.length) {
                return;
            }

            if (!tableData || tableData.length === 0) {
                tableBody.html('<tr><td colspan="9" class="text-center py-4 text-muted">ไม่มีข้อมูล</td></tr>');
                return;
            }

            var html = '';
            var self = this;
            tableData.forEach(function (row) {
                html += '<tr>';
                html += '<td>[' + row.department_code + '] ' + row.department_name + '</td>';
                html += '<td class="text-end">' + self._formatNumber(row.budget_source_1) + '</td>';
                html += '<td class="text-end">' + self._formatNumber(row.budget_source_2) + '</td>';
                html += '<td class="text-end">' + self._formatNumber(row.budget_other) + '</td>';
                html += '<td class="text-center text-muted">' + row.q1 + '</td>';
                html += '<td class="text-center text-muted">' + row.q2 + '</td>';
                html += '<td class="text-center text-muted">' + row.q3 + '</td>';
                html += '<td class="text-center text-muted">' + row.q4 + '</td>';
                html += '<td class="text-end fw-bold">' + self._formatNumber(row.total_budget) + '</td>';
                html += '</tr>';
            });

            tableBody.html(html);
        },

        _formatNumber: function (num) {
            if (num === null || num === undefined) {
                return '0.00';
            }
            return num.toLocaleString('th-TH', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        },
    });

    publicWidget.registry.KmitlProjectDashboard = DashboardWidget;

    return DashboardWidget;
});
