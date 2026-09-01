import { app } from "../../scripts/app.js";

const _NODE = "VideoResultNode";
const _WIDGET = "volume";
const _DEFAULT = 50;

const nodes = new Set();

const getVolume = (node) => {
    const percent = node.widgets?.find((x) => x.name === _WIDGET)?.value;

    if (typeof percent !== "number") return null;

    return Math.min(Math.max(percent, 0), 100) / 100;
};

// El reproductor cuelga del DOM widget (nodos de canvas) o del elemento del nodo (nodos Vue).
const getRoot = (node) => node.videoContainer ?? document.querySelector(`[data-node-id="${node.id}"]`);

const findNode = (video) => {
    const nodeId = video.closest("[data-node-id]")?.dataset?.nodeId;

    for (const node of nodes) {
        if (node.videoContainer?.contains(video)) return node;

        if (nodeId !== undefined && String(node.id) === nodeId) return node;
    }

    return null;
};

const setVolume = (video, node) => {
    const volume = getVolume(node);

    if (volume !== null) video.volume = volume;
};

app.registerExtension({
    name: "AstroCorp.VideoResultWidget",
    setup() {
        // Cada generación monta un <video> nuevo, siempre al 100%.
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const added of mutation.addedNodes) {
                    if (!(added instanceof HTMLElement)) continue;

                    const videos = added instanceof HTMLVideoElement ? [added] : added.querySelectorAll("video");

                    for (const video of videos) {
                        const node = findNode(video);

                        if (node) setVolume(video, node);
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== _NODE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            nodes.add(this);

            this.addWidget(
                "slider",
                _WIDGET,
                _DEFAULT,
                () => getRoot(this)?.querySelectorAll("video").forEach((video) => setVolume(video, this)),
                { min: 0, max: 100, step2: 1, precision: 0 }
            );

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);
        };

        const onRemoved = nodeType.prototype.onRemoved;

        nodeType.prototype.onRemoved = function () {
            nodes.delete(this);

            onRemoved?.apply(this, arguments);
        };
    },
});
