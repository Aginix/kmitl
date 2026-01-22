document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    if (typeof Chart !== 'undefined' && typeof chartData !== 'undefined') {
        initCharts();
    } else if (typeof chartData !== 'undefined') {
        // Load Chart.js from CDN if not available
        var script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        script.onload = function() {
            initCharts();
        };
        document.head.appendChild(script);
    }

    // Add event listeners
    setupEventListeners();
});

function initCharts() {
    if (!chartData) return;

    // Budget Bar Chart
    var budgetCtx = document.getElementById('budgetBarChart');
    if (budgetCtx && chartData.budget_by_department) {
        new Chart(budgetCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: chartData.budget_by_department.labels,
                datasets: [{
                    label: 'งบประมาณ (บาท)',
                    data: chartData.budget_by_department.data,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return (value / 1000000).toFixed(1) + 'M';
                                } else if (value >= 1000) {
                                    return (value / 1000).toFixed(0) + 'K';
                                }
                                return value.toLocaleString('th-TH');
                            },
                            font: { size: 10 }
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            font: { size: 9 },
                            callback: function(value, index) {
                                var label = this.getLabelForValue(value);
                                if (label && label.length > 12) {
                                    return label.substring(0, 12) + '...';
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }

    // Trend Line Chart
    var trendCtx = document.getElementById('trendLineChart');
    if (trendCtx && chartData.monthly_trend) {
        new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.monthly_trend.labels,
                datasets: [{
                    label: 'โครงการ',
                    data: chartData.monthly_trend.data,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        display: false
                    },
                    x: {
                        display: false
                    }
                }
            }
        });
    }
}

function setupEventListeners() {
    // Filter dropdowns - auto apply on change
    var filterIds = ['fiscal_year_filter', 'department_filter', 'activity_filter', 'fund_filter', 'source_filter'];
    filterIds.forEach(function(id) {
        var element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', applyFilters);
        }
    });

    // Search on Enter key
    var searchInput = document.getElementById('search_input');
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                applyFilters();
            }
        });
    }
}

function applyFilters() {
    var params = new URLSearchParams();

    var fiscalYear = document.getElementById('fiscal_year_filter');
    if (fiscalYear && fiscalYear.value) {
        params.set('fiscal_year_id', fiscalYear.value);
    }

    var department = document.getElementById('department_filter');
    if (department && department.value) {
        params.set('department_id', department.value);
    }

    var activity = document.getElementById('activity_filter');
    if (activity && activity.value) {
        params.set('activity_id', activity.value);
    }

    var fund = document.getElementById('fund_filter');
    if (fund && fund.value) {
        params.set('fund_id', fund.value);
    }

    var source = document.getElementById('source_filter');
    if (source && source.value) {
        params.set('source_id', source.value);
    }

    var search = document.getElementById('search_input');
    if (search && search.value) {
        params.set('search', search.value);
    }

    // Preserve current state/tab
    var currentTab = document.querySelector('#stateTabs .nav-link.active');
    if (currentTab && currentTab.dataset.state) {
        params.set('state', currentTab.dataset.state);
    }

    window.location.href = '/project/dashboard?' + params.toString();
}

function setTab(state) {
    var params = new URLSearchParams(window.location.search);
    params.set('state', state);
    params.set('page', '1');  // Reset to first page
    window.location.href = '/project/dashboard?' + params.toString();
}

function goToPage(page) {
    var params = new URLSearchParams(window.location.search);
    params.set('page', page);
    window.location.href = '/project/dashboard?' + params.toString();
}
