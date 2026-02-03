var dashboardChart = null;

document.addEventListener('DOMContentLoaded', function() {
    // Load Apache ECharts from CDN
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
    script.onload = function() {
        // Load initial data after ECharts is ready
        loadDashboardData();
    };
    document.head.appendChild(script);

    // Initialize filters from URL and sync URL state
    initFiltersFromUrl();

    // Setup filter event listeners
    setupEventListeners();
});

function initFiltersFromUrl() {
    var params = new URLSearchParams(window.location.search);

    var fiscalYearFilter = document.getElementById('fiscal_year_filter');
    var departmentFilter = document.getElementById('department_filter');

    // Sync URL with current filter state (ensure URL always reflects filters)
    var needsUpdate = false;
    var newParams = new URLSearchParams();

    if (fiscalYearFilter && fiscalYearFilter.value) {
        var urlFiscalYear = params.get('fiscal_year_id');
        if (urlFiscalYear !== fiscalYearFilter.value) {
            needsUpdate = true;
        }
        newParams.set('fiscal_year_id', fiscalYearFilter.value);
    }

    if (departmentFilter && departmentFilter.value) {
        newParams.set('department_id', departmentFilter.value);
    }

    // Update URL without reload to reflect current filters
    if (needsUpdate || (fiscalYearFilter && fiscalYearFilter.value && !params.has('fiscal_year_id'))) {
        var newUrl = '/project/dashboard?' + newParams.toString();
        history.replaceState(null, '', newUrl);
    }
}

function setupEventListeners() {
    var fiscalYearFilter = document.getElementById('fiscal_year_filter');
    var departmentFilter = document.getElementById('department_filter');

    if (fiscalYearFilter) {
        fiscalYearFilter.addEventListener('change', onFilterChange);
    }
    if (departmentFilter) {
        departmentFilter.addEventListener('change', onFilterChange);
    }
}

function onFilterChange() {
    // Update URL
    updateUrl();
    // Reload data via API
    loadDashboardData();
}

function updateUrl() {
    var params = new URLSearchParams();

    var fiscalYear = document.getElementById('fiscal_year_filter');
    if (fiscalYear && fiscalYear.value) {
        params.set('fiscal_year_id', fiscalYear.value);
    }

    var department = document.getElementById('department_filter');
    if (department && department.value) {
        params.set('department_id', department.value);
    }

    var newUrl = '/project/dashboard?' + params.toString();
    history.pushState(null, '', newUrl);
}

function loadDashboardData() {
    var fiscalYearFilter = document.getElementById('fiscal_year_filter');
    var departmentFilter = document.getElementById('department_filter');

    var fiscalYearId = fiscalYearFilter ? fiscalYearFilter.value : null;
    var departmentId = departmentFilter ? departmentFilter.value : null;

    // Show loading state
    showLoadingState();

    // Call API
    fetch('/project/dashboard/api', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: {
                fiscal_year_id: fiscalYearId,
                department_id: departmentId || null,
            },
            id: Date.now(),
        }),
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        if (data.result) {
            updateDashboard(data.result);
        } else if (data.error) {
            console.error('API Error:', data.error);
            showErrorState();
        }
    })
    .catch(function(error) {
        console.error('Fetch Error:', error);
        showErrorState();
    });
}

function showLoadingState() {
    // Show loading for stats
    var statIds = ['stat-total', 'stat-education', 'stat-academic', 'stat-industrial', 'stat-social'];
    statIds.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<span class="placeholder-glow"><span class="placeholder col-4"></span></span>';
        }
    });

    // Show loading for table
    var tableBody = document.getElementById('budget-table-body');
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';
    }
}

function showErrorState() {
    // Show error for stats
    var statIds = ['stat-total', 'stat-education', 'stat-academic', 'stat-industrial', 'stat-social'];
    statIds.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.textContent = '-';
        }
    });

    // Show error for table
    var tableBody = document.getElementById('budget-table-body');
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-danger">เกิดข้อผิดพลาดในการโหลดข้อมูล</td></tr>';
    }
}

function updateDashboard(data) {
    // Update statistics
    updateStats(data.impact_stats);

    // Update chart
    updateChart(data.chart_data);

    // Update table
    updateTable(data.department_budget_table);
}

function updateStats(stats) {
    document.getElementById('stat-total').textContent = stats.total || 0;
    document.getElementById('stat-education').textContent = stats.education || 0;
    document.getElementById('stat-academic').textContent = stats.academic || 0;
    document.getElementById('stat-industrial').textContent = stats.industrial || 0;
    document.getElementById('stat-social').textContent = stats.social || 0;
}

function updateChart(chartData) {
    if (typeof echarts === 'undefined' || !chartData || !chartData.budget_by_impact) {
        return;
    }

    var chartDom = document.getElementById('budgetPieChart');
    if (!chartDom) {
        return;
    }

    // Initialize or get existing chart
    if (!dashboardChart) {
        dashboardChart = echarts.init(chartDom);

        // Handle window resize
        window.addEventListener('resize', function() {
            dashboardChart.resize();
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
    var pieData = chartData.budget_by_impact.map(function(item) {
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
            formatter: function(params) {
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
                    formatter: function(params) {
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

    dashboardChart.setOption(option, true);
}

function updateTable(tableData) {
    var tableBody = document.getElementById('budget-table-body');
    if (!tableBody) {
        return;
    }

    if (!tableData || tableData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">ไม่มีข้อมูล</td></tr>';
        return;
    }

    var html = '';
    tableData.forEach(function(row) {
        html += '<tr>';
        html += '<td>[' + row.department_code + '] ' + row.department_name + '</td>';
        html += '<td class="text-end">' + formatNumber(row.budget_source_1) + '</td>';
        html += '<td class="text-end">' + formatNumber(row.budget_source_2) + '</td>';
        html += '<td class="text-end">' + formatNumber(row.budget_other) + '</td>';
        html += '<td class="text-center text-muted">' + row.q1 + '</td>';
        html += '<td class="text-center text-muted">' + row.q2 + '</td>';
        html += '<td class="text-center text-muted">' + row.q3 + '</td>';
        html += '<td class="text-center text-muted">' + row.q4 + '</td>';
        html += '<td class="text-end fw-bold">' + formatNumber(row.total_budget) + '</td>';
        html += '</tr>';
    });

    tableBody.innerHTML = html;
}

function formatNumber(num) {
    if (num === null || num === undefined) {
        return '0.00';
    }
    return num.toLocaleString('th-TH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
