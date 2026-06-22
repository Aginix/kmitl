/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Landing page shown (as a Home Action) to backend-UI users who have no
 * application access yet. It explains the situation and lists the system
 * administrators to contact.
 *
 * Self-healing: if the user has meanwhile been granted real apps, we forward
 * them to the first one instead of trapping them on this page - so a stale
 * Home Action never needs manual clean-up.
 */
export class ContactAdmin extends Component {
    setup() {
        this.orm = useService("orm");
        this.menu = useService("menu");
        this.state = useState({ admins: [], forwarding: false });

        onWillStart(async () => {
            const apps = this.menu.getApps().filter((app) => app.actionID);
            if (apps.length) {
                this.state.forwarding = true;
                this.menu.selectMenu(apps[0]);
                return;
            }
            try {
                this.state.admins = await this.orm.call("res.users", "get_access_admins", []);
            } catch {
                this.state.admins = [];
            }
        });
    }
}

ContactAdmin.template = "kmitl_backend_user.ContactAdmin";

registry.category("actions").add("contact_admin", ContactAdmin);
