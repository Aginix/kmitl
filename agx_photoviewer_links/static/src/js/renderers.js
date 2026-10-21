/** @odoo-module **/

import {_lt, _t} from "@web/core/l10n/translation";
import {escape} from "@web/core/utils/strings";
import {parseOdooLink} from "@web_attachment_link/link_utils";
import {photoviewerRenderers} from "@agx_photoviewer/js/photoviewer";

// Before the file renderers (sequence 50): a link's mimetype is guessed from
// its name, so a link named "report.pdf" must not reach the PDF renderer.
const LINK_SEQUENCE = 10;
const CATCH_ALL_SEQUENCE = 20;

const YOUTUBE_ID = /^[\w-]{11}$/;
const DRIVE_ID = /^[\w-]+$/;

function parseUrl(attachment) {
    if (attachment.type !== "url" || !attachment.url) {
        return null;
    }
    try {
        return new URL(attachment.url, window.location.origin);
    } catch {
        return null;
    }
}

function getYoutubeId(attachment) {
    const url = parseUrl(attachment);
    if (!url) {
        return null;
    }
    const host = url.hostname.replace(/^(www|m)\./, "");
    let id = null;
    if (host === "youtu.be") {
        id = url.pathname.split("/")[1];
    } else if (["youtube.com", "youtube-nocookie.com"].includes(host)) {
        const [, kind, value] = url.pathname.split("/");
        id = kind === "watch" ? url.searchParams.get("v") : value;
        if (!["watch", "embed", "shorts", "live", "v"].includes(kind)) {
            id = null;
        }
    }
    return id && YOUTUBE_ID.test(id) ? id : null;
}

/** The embeddable address of a Google Drive item, or null. */
function getDrivePreviewUrl(attachment) {
    const url = parseUrl(attachment);
    if (!url) {
        return null;
    }
    const parts = url.pathname.split("/");
    if (url.hostname === "docs.google.com") {
        // /document|spreadsheets|presentation/d/<id>/…
        const kind = parts[1];
        const id = parts[3];
        if (
            ["document", "spreadsheets", "presentation"].includes(kind) &&
            parts[2] === "d" &&
            DRIVE_ID.test(id)
        ) {
            return `https://docs.google.com/${kind}/d/${id}/preview`;
        }
    } else if (url.hostname === "drive.google.com") {
        // /file/d/<id>/…, /drive/[u/<n>/]folders/<id>, /open?id=<id>
        const fileIndex = parts.indexOf("d");
        if (parts[1] === "file" && fileIndex === 2 && DRIVE_ID.test(parts[3])) {
            return `https://drive.google.com/file/d/${parts[3]}/preview`;
        }
        const folderIndex = parts.indexOf("folders");
        const folderId = folderIndex > 0 && parts[folderIndex + 1];
        if (folderId && DRIVE_ID.test(folderId)) {
            return `https://drive.google.com/embeddedfolderview?id=${folderId}#list`;
        }
        const openId = url.searchParams.get("id");
        if (parts[1] === "open" && openId && DRIVE_ID.test(openId)) {
            return `https://drive.google.com/file/d/${openId}/preview`;
        }
    }
    return null;
}

function iconNode(className) {
    const icon = document.createElement("i");
    icon.className = `fa ${className} fa-2x text-muted`;
    return icon;
}

function renderFrame(page, src) {
    const iframe = document.createElement("iframe");
    iframe.src = src;
    iframe.allow = "autoplay; encrypted-media; fullscreen; picture-in-picture";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    page.replaceChildren(iframe);
}

/**
 * A Link Card: a title, a line above it and the given buttons
 * ([{label, icon, primary, onClick}]).
 */
function renderCard(page, {icon, overline, title, buttons}) {
    const card = document.createElement("div");
    card.className = "o_agx_photoviewer_link_card m-auto text-center p-4";
    card.innerHTML = `
        <i class="fa ${icon} fa-3x text-muted mb-3"></i>
        <div class="small text-muted text-break">${escape(overline || "")}</div>
        <div class="fs-4 mb-3 text-break">${escape(title || "")}</div>
        <div class="d-flex flex-wrap justify-content-center gap-2"></div>`;
    const actions = card.lastElementChild;
    for (const {label, icon: buttonIcon, primary, onClick} of buttons) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `btn ${primary ? "btn-primary" : "btn-secondary"}`;
        button.innerHTML = `<i class="fa ${buttonIcon} me-1"></i>${escape(label)}`;
        button.addEventListener("click", onClick);
        actions.append(button);
    }
    page.replaceChildren(card);
}

function openInNewTab(attachment) {
    window.open(attachment.url, "_blank", "noopener");
}

// เปิดต้นทาง: replaces Download, which means nothing for a link.
const openAtOriginButton = {
    title: _lt("Open at origin"),
    text: '<i class="fa fa-external-link"></i>',
    click: openInNewTab,
};

const newTabButton = (attachment) => ({
    label: _t("Open in new tab"),
    icon: "fa-external-link",
    onClick: () => openInNewTab(attachment),
});

/** Open the record or action of an Odoo Link in the current webclient. */
function openOdooLink(env, params) {
    const id = Number(params.id);
    if (params.model && id) {
        return env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: params.model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    return env.services.action.doAction(Number(params.action) || params.action);
}

async function renderOdooLink(attachment, page, {env, close}) {
    const params = parseOdooLink(attachment.url);
    const info = await env.services.orm.call("ir.attachment", "get_odoo_link_info", [
        attachment.url,
    ]);
    if (info.error) {
        renderCard(page, {
            icon: info.error === "access" ? "fa-lock" : "fa-chain-broken",
            overline: attachment.name,
            title:
                info.error === "access"
                    ? _t("You do not have access to this document.")
                    : _t("The document this link points to no longer exists."),
            buttons: [],
        });
        return;
    }
    renderCard(page, {
        icon: "fa-file-text-o",
        overline: info.model_label,
        title: info.name,
        buttons: [
            {
                label: _t("Open"),
                icon: "fa-arrow-right",
                primary: true,
                onClick: () => {
                    close();
                    openOdooLink(env, params);
                },
            },
            newTabButton(attachment),
        ],
    });
}

const renderers = {
    youtube: {
        sequence: LINK_SEQUENCE,
        match: (attachment) => Boolean(getYoutubeId(attachment)),
        render(attachment, page) {
            renderFrame(
                page,
                `https://www.youtube.com/embed/${getYoutubeId(attachment)}`
            );
        },
        thumbnail(attachment) {
            const image = document.createElement("img");
            image.loading = "lazy";
            image.src = `https://img.youtube.com/vi/${getYoutubeId(
                attachment
            )}/default.jpg`;
            image.addEventListener("error", () =>
                image.replaceWith(iconNode("fa-youtube-play"))
            );
            return image;
        },
    },
    google_drive: {
        sequence: LINK_SEQUENCE,
        match: (attachment) => Boolean(getDrivePreviewUrl(attachment)),
        render(attachment, page) {
            // Shows only what the viewer's own Google session may see.
            renderFrame(page, getDrivePreviewUrl(attachment));
        },
        thumbnail: () => iconNode("fa-google"),
    },
    odoo_link: {
        sequence: LINK_SEQUENCE,
        match: (attachment) =>
            attachment.type === "url" && Boolean(parseOdooLink(attachment.url)),
        render: renderOdooLink,
        thumbnail: () => iconNode("fa-file-text-o"),
    },
    web_link: {
        sequence: CATCH_ALL_SEQUENCE,
        match: (attachment) => Boolean(parseUrl(attachment)),
        render(attachment, page) {
            const url = parseUrl(attachment);
            renderCard(page, {
                icon: "fa-globe",
                overline: url.hostname,
                title: attachment.name,
                buttons: [{...newTabButton(attachment), primary: true}],
            });
        },
        thumbnail: () => iconNode("fa-globe"),
    },
};

for (const [name, {sequence, ...renderer}] of Object.entries(renderers)) {
    photoviewerRenderers.add(
        name,
        {...renderer, headerButton: openAtOriginButton},
        {sequence}
    );
}
