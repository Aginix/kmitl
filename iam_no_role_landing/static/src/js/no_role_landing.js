/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";

export class NoRoleLanding extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            contactMessage: "",
            userName: "",
            checking: false,
        });
        onWillStart(async () => {
            const info = await this.orm.call("res.users", "get_no_role_landing_info", []);
            this.state.contactMessage = info.contact_message;
            this.state.userName = info.user_name;
            this.state.loading = false;
        });
    }

    async onCheckRole() {
        this.state.checking = true;
        try {
            const result = await this.orm.call("res.users", "check_role_status", []);
            if (result.has_role) {
                // Hard reload so the session's group cache and menus are refreshed.
                window.location = "/web";
            } else {
                this.notification.add(
                    _t("ยังไม่ได้รับสิทธิ์ กรุณาติดต่อผู้ดูแลระบบ"),
                    {type: "warning"}
                );
            }
        } finally {
            this.state.checking = false;
        }
    }

    onLogout() {
        window.location = "/web/session/logout";
    }
}

NoRoleLanding.template = "iam_no_role_landing.Landing";
NoRoleLanding.props = ["*"];

registry.category("actions").add("iam_no_role_landing.landing", NoRoleLanding);
