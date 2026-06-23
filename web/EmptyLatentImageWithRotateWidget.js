import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "AstroCorp.EmptyLatentImageWithRotateWidget",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "EmptyLatentImageWithRotate") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            const swapWh = () => {
                const w = this.widgets?.find((x) => x.name === "width");
                const h = this.widgets?.find((x) => x.name === "height");

                if (!w || !h) return;

                const tmp = w.value;

                w.value = h.value;
                h.value = tmp;

                if (typeof w.callback === "function") w.callback(w.value);

                if (typeof h.callback === "function") h.callback(h.value);

                this.setDirtyCanvas(true, true);
            };

            if (typeof this.addWidget === "function") {
                // LiteGraph: arg2 is the label drawn on the canvas (arg3 is value / often unused for buttons).
                const rotateBtn = this.addWidget(
                    "button",
                    "⟳ Swap width / height",
                    null,
                    swapWh
                );
                const widgets = this.widgets;
                const batchIdx = widgets?.findIndex((x) => x.name === "batch_size") ?? -1;
                const btn =
                    rotateBtn ??
                    widgets?.filter((x) => x.type === "button").pop();
                const btnIdx = btn ? widgets.indexOf(btn) : -1;

                if (btn && batchIdx >= 0 && btnIdx > batchIdx) {
                    widgets.splice(btnIdx, 1);
                    widgets.splice(batchIdx, 0, btn);
                }
            }

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);
        };
    },
});
