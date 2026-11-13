import { app } from "../../scripts/app.js";

const _NODE = "TextFileEditorNode";
const _SELECT = "Select file";
const _SAVE_DELAY = 2000;
const _MAX_STEPS = 10;
const _DB = "astrocorp-text-file-editor";
const _STORE = "handles";

const getWidget = (node, name) => node.widgets.find((widget) => widget.name === name);

const openDb = () => new Promise((resolve, reject) => {
    const request = indexedDB.open(_DB, 1);

    request.onupgradeneeded = () => request.result.createObjectStore(_STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
});

const withStore = async (mode, run) => {
    const db = await openDb();

    try {
        return await new Promise((resolve, reject) => {
            const transaction = db.transaction(_STORE, mode);
            const result = run(transaction.objectStore(_STORE));

            transaction.oncomplete = () => resolve(result.result);
            transaction.onerror = () => reject(transaction.error);
        });
    } finally {
        db.close();
    }
};

const rememberHandle = (id, handle) => withStore("readwrite", (store) => store.put(handle, id));

const recallHandle = (id) => withStore("readonly", (store) => store.get(id));

const updateButtons = (node) => {
    const editor = node.textEditor;
    // Un cambio pendiente de guardar cuenta como un paso más y descarta los pasos "futuros".
    const undoSteps = editor.index + (editor.timer ? 1 : 0);
    const redoSteps = editor.timer ? 0 : editor.states.length - 1 - editor.index;

    editor.undo.label = `Undo (${undoSteps})`;
    editor.undo.disabled = undoSteps === 0;
    editor.redo.label = `Redo (${redoSteps})`;
    editor.redo.disabled = redoSteps === 0;

    node.setDirtyCanvas(true, false);
};

const resetHistory = (node) => {
    const editor = node.textEditor;

    clearTimeout(editor.timer);

    editor.timer = null;
    editor.states = [getWidget(node, "text").value];
    editor.index = 0;

    updateButtons(node);
};

const setText = (node, text) => {
    const editor = node.textEditor;

    editor.applying = true;
    getWidget(node, "text").value = text;
    editor.applying = false;
};

// Las escrituras se encadenan para que lleguen al disco en el mismo orden en que se hicieron.
const saveText = (node, text) => {
    const editor = node.textEditor;
    const handle = editor.handle;
    const name = node.properties.file_name || "file";

    if (!handle) {
        if (!editor.warned) {
            editor.warned = true;
            alert(`Select ${name} again to save changes.`);
        }

        return;
    }

    editor.saving = editor.saving
        .then(async () => {
            const writable = await handle.createWritable();

            await writable.write(text);
            await writable.close();
        })
        .catch((error) => alert(error.message ?? error));
};

const commitText = (node) => {
    const editor = node.textEditor;
    const text = getWidget(node, "text").value;

    clearTimeout(editor.timer);

    editor.timer = null;

    if (text !== editor.states[editor.index]) {
        editor.states.length = editor.index + 1;
        editor.states.push(text);

        if (editor.states.length > _MAX_STEPS + 1) editor.states.shift();

        editor.index = editor.states.length - 1;

        saveText(node, text);
    }

    updateButtons(node);
};

const onEdit = (node) => {
    const editor = node.textEditor;

    // Asignar el valor por código (deshacer, cargar archivo) también dispara el callback del widget.
    if (editor.applying) return;
    if (!editor.timer && getWidget(node, "text").value === editor.states[editor.index]) return;

    clearTimeout(editor.timer);

    editor.timer = setTimeout(() => commitText(node), _SAVE_DELAY);

    updateButtons(node);
};

const moveHistory = (node, delta) => {
    commitText(node);

    const editor = node.textEditor;
    const index = editor.index + delta;

    if (index < 0 || index >= editor.states.length) return;

    editor.index = index;
    setText(node, editor.states[index]);

    saveText(node, editor.states[index]);
    updateButtons(node);
};

const selectFile = async (node) => {
    if (!window.showOpenFilePicker) {
        alert("Use Chrome or Edge to pick a .txt file and save changes back to it.");

        return;
    }

    // Lo que se estuviera escribiendo se guarda en el archivo anterior antes de cambiar.
    commitText(node);

    let handle;

    try {
        [handle] = await window.showOpenFilePicker({
            multiple: false,
            excludeAcceptAllOption: true,
            types: [{ description: "Text", accept: { "text/plain": [".txt"] } }],
        });
    } catch (error) {
        if (error.name !== "AbortError") alert(error.message ?? error);

        return;
    }

    if (!handle.name.toLowerCase().endsWith(".txt")) {
        alert("Select a .txt file.");

        return;
    }

    try {
        const file = await handle.getFile();

        node.properties.file_id ??= crypto.randomUUID();
        node.properties.file_name = handle.name;
        node.textEditor.handle = handle;
        node.textEditor.warned = false;
        node.textEditor.select.label = handle.name;

        await rememberHandle(node.properties.file_id, handle);
        setText(node, await file.text());
        resetHistory(node);
    } catch (error) {
        alert(error.message ?? error);
    }
};

const restoreHandle = async (node) => {
    const id = node.properties?.file_id;

    if (!id) return;

    const handle = await recallHandle(id);
    const permission = await handle?.queryPermission?.({ mode: "readwrite" });

    if (permission === "granted") node.textEditor.handle = handle;
};

app.registerExtension({
    name: "AstroCorp.TextFileEditorWidget",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== _NODE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            this.properties ??= {};

            this.textEditor = {
                handle: null,
                states: [""],
                index: 0,
                timer: null,
                applying: false,
                warned: false,
                saving: Promise.resolve(),
            };

            const textWidget = getWidget(this, "text");
            const textCallback = textWidget.callback;

            textWidget.callback = (...args) => {
                textCallback?.(...args);
                onEdit(this);
            };

            this.textEditor.select = this.addWidget("button", _SELECT, null, () => selectFile(this));
            this.textEditor.undo = this.addWidget("button", "Undo", null, () => moveHistory(this, -1));
            this.textEditor.redo = this.addWidget("button", "Redo", null, () => moveHistory(this, 1));
            this.widgets = [this.textEditor.select, textWidget, this.textEditor.undo, this.textEditor.redo];

            if (this.properties.file_name) this.textEditor.select.label = this.properties.file_name;

            updateButtons(this);
            resetHistory(this);

            this.setSize(this.computeSize(this.size));
            this.setDirtyCanvas(true, false);
        };

        const onConfigure = nodeType.prototype.onConfigure;

        // Un workflow guardado conserva su texto: el historial parte de él y no se reescribe el archivo.
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);

            if (this.properties.file_name) this.textEditor.select.label = this.properties.file_name;

            resetHistory(this);
            restoreHandle(this);
        };

        const onRemoved = nodeType.prototype.onRemoved;

        nodeType.prototype.onRemoved = function () {
            if (this.textEditor.timer) commitText(this);

            onRemoved?.apply(this, arguments);
        };
    },
});
