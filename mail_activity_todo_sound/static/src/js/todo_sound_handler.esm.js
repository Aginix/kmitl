/** @odoo-module **/

import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";

/**
 * Play a short sound when a NEW Todo lands in the inbox.
 *
 * The server (mail_activity_todo core) pings "mail_activity_todo/updated" on
 * create/write/unlink; only a create carries {sound: true} (and only when the
 * recipient's per-user preference is on — decided server-side, ADR-0014). This
 * service obeys payload.sound: play only when true, only on the main tab (so a
 * user with several tabs open hears one ding, not N).
 */
export const todoSoundHandler = {
    dependencies: ["bus_service", "multi_tab"],

    start(env, { bus_service, multi_tab }) {
        let audio = null;
        if (typeof Audio !== "undefined") {
            audio = new Audio();
            audio.src = audio.canPlayType("audio/ogg; codecs=vorbis")
                ? url("/mail_activity_todo_sound/static/src/audio/ting.ogg")
                : url("/mail_activity_todo_sound/static/src/audio/ting.mp3");
        }

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type !== "mail_activity_todo/updated") {
                    continue;
                }
                if (!payload || !payload.sound) {
                    continue;
                }
                if (!multi_tab.isOnMainTab()) {
                    continue;
                }
                if (audio) {
                    audio.play().catch(() => {});
                }
            }
        });
    },
};

registry
    .category("services")
    .add("mail_activity_todo_sound.sound_handler", todoSoundHandler);
