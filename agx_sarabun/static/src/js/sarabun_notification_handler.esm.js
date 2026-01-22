/** @odoo-module **/

import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";

export const sarabunNotificationHandler = {
    dependencies: ["bus_service", "multi_tab"],

    start(env, { bus_service, multi_tab }) {
        // Request notification permission on startup
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }

        // Create audio element (check format support like mail module)
        let audio = null;
        if (typeof Audio !== "undefined") {
            audio = new Audio();
            audio.src = audio.canPlayType("audio/ogg; codecs=vorbis")
                ? url("/agx_sarabun/static/src/audio/ting.ogg")
                : url("/agx_sarabun/static/src/audio/ting.mp3");
        }

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "sarabun_inbox/updated") {
                    // Trigger systray update
                    env.bus.trigger("sarabun_inbox_updated", payload);

                    // Only play sound/notification on main tab
                    if (!multi_tab.isOnMainTab()) {
                        continue;
                    }

                    // Show browser notification
                    if ("Notification" in window && Notification.permission === "granted") {
                        const notification = new Notification("เอกสารใหม่", {
                            body: payload.subject || "คุณมีเอกสารใหม่รอดำเนินการ",
                            icon: "/agx_sarabun/static/description/icon.png",
                            tag: "sarabun-inbox",
                        });
                        notification.onclick = () => {
                            window.focus();
                            notification.close();
                        };
                    }

                    // Play notification sound
                    if (audio) {
                        audio.play().catch(() => {});
                    }
                }
            }
        });
    },
};

registry.category("services").add("sarabunNotificationHandler", sarabunNotificationHandler);
