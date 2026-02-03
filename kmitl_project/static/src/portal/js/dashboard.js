document.addEventListener('DOMContentLoaded', function() {
    // Load Apache ECharts from CDN
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
    script.onload = function() {
        initCharts();
    };
    document.head.appendChild(script);

    // Setup filter event listeners
    setupEventListeners();
});

function initCharts() {
    if (typeof chartData === 'undefined' || !chartData.budget_by_impact) {
        return;
    }

    var chartDom = document.getElementById('budgetPieChart');
    if (!chartDom) {
        return;
    }

    var myChart = echarts.init(chartDom);

    // Define colors for each Impact category
    var impactColors = {
        'Education': '#17a2b8',  // info color
        'Academic': '#28a745',   // success color
        'Industrial': '#ffc107', // warning color
        'Social': '#dc3545',     // danger color
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

    myChart.setOption(option);

    // Handle window resize
    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

function setupEventListeners() {
    var fiscalYearFilter = document.getElementById('fiscal_year_filter');
    var departmentFilter = document.getElementById('department_filter');

    if (fiscalYearFilter) {
        fiscalYearFilter.addEventListener('change', applyFilters);
    }
    if (departmentFilter) {
        departmentFilter.addEventListener('change', applyFilters);
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

    window.location.href = '/project/dashboard?' + params.toString();
}
