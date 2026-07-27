/** @odoo-module **/

import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";

/**
 * Bridges the engine's realtime bus notifications to the inbox systray.
 *
 * The routing engine pushes "sarabun_inbox/updated" to each snapshot holder when
 * a step activates (payload carries subject/document_id) or clears (payload
 * {refresh:true}). This service re-broadcasts it on the env bus (the systray
 * listens), and — only for genuinely new work, only on the main tab — plays a
 * sound and shows a browser notification.
 */
export const sarabunNotificationHandler = {
    dependencies: ["bus_service", "multi_tab"],

    start(env, { bus_service, multi_tab }) {
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }

        let audio = null;
        if (typeof Audio !== "undefined") {
            audio = new Audio();
            audio.src = audio.canPlayType("audio/ogg; codecs=vorbis")
                ? url("/agx_sarabun/static/src/audio/ting.ogg")
                : url("/agx_sarabun/static/src/audio/ting.mp3");
        }

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type !== "sarabun_inbox/updated") {
                    continue;
                }
                // Always refresh the systray badge/list.
                env.bus.trigger("sarabun_inbox_updated", payload);

                if (!multi_tab.isOnMainTab()) {
                    continue;
                }
                // Sound/desktop notification only for genuinely new work.
                const isNewWork = payload && (payload.subject || payload.document_id);
                if (!isNewWork) {
                    continue;
                }
                if ("Notification" in window && Notification.permission === "granted") {
                    const notification = new Notification("หนังสือใหม่", {
                        body: payload.subject || "คุณมีหนังสือใหม่รอดำเนินการ",
                        icon: "/agx_sarabun/static/description/icon.png",
                        tag: "sarabun-inbox",
                    });
                    notification.onclick = () => {
                        window.focus();
                        notification.close();
                    };
                }
                if (audio) {
                    audio.play().catch(() => {});
                }
            }
        });
    },
};

registry.category("services").add("sarabunNotificationHandler", sarabunNotificationHandler);
