odoo.define('dev_login.dev_login', function (require) {
    'use strict';

    var core = require('web.core');
    var ajax = require('web.ajax');

    // Show dev login on login page
    function initDevLogin() {
        // Check if we're on login page
        var isLoginPage = window.location.pathname === '/web/login' || 
                         document.querySelector('.oe_login_form') !== null;
        
        if (!isLoginPage) {
            return;
        }

        // Show the dev login container
        var devContainer = document.querySelector('.dev-login-container');
        if (devContainer) {
            devContainer.style.display = 'block';
        }

        // Add click handler for admin login button
        var adminBtn = document.getElementById('dev_login_admin_btn');
        if (adminBtn) {
            adminBtn.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Show loading state
                adminBtn.disabled = true;
                adminBtn.innerHTML = '<i class="fa fa-spinner fa-spin"/> Logging in...';
                
                // Create a form and submit to dev login endpoint
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = '/dev_login/admin';
                form.style.display = 'none';
                
                document.body.appendChild(form);
                form.submit();
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDevLogin);
    } else {
        initDevLogin();
    }

    return {
        initDevLogin: initDevLogin
    };
});