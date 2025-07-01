import copy
from typing import Any, Dict
from uuid import uuid4

import y_py as Y

from .utils import cast_all


class YBaseDoc:
    def __init__(self, ydoc: Y.YDoc):
        self._ydoc = ydoc
        self._ystate = self._ydoc.get_map("state")
        self._subscriptions = {}

    @property
    def ystate(self):
        return self._ystate

    @property
    def ydoc(self):
        return self._ydoc

    @property
    def source(self):
        return self.get()

    @source.setter
    def source(self, value):
        return self.set(value)

    @property
    def dirty(self) -> None:
        return self._ystate["dirty"]

    @dirty.setter
    def dirty(self, value: bool) -> None:
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "dirty", value)

    @property
    def path(self) -> None:
        return self._ystate.get("path")

    @path.setter
    def path(self, value: str) -> None:
        with self._ydoc.begin_transaction() as t:
            self._ystate.set(t, "path", value)

    def get(self):
        raise RuntimeError("Y document get not implemented")

    def set(self, value):
        raise RuntimeError("Y document set not implemented")

    def observe(self, callback):
        raise RuntimeError("Y document observe not implemented")

    def unobserve(self):
        for k, v in self._subscriptions.items():
            k.unobserve(v)
        self._subscriptions = {}


class YFile(YBaseDoc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ysource = self._ydoc.get_text("source")

    def get(self):
        return str(self._ysource)

    def set(self, value):
        with self._ydoc.begin_transaction() as t:
            # clear document
            source_len = len(self._ysource)
            if source_len:
                self._ysource.delete_range(t, 0, source_len)
            # initialize document
            if value:
                self._ysource.extend(t, value)

    def observe(self, callback):
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ysource] = self._ysource.observe(callback)


class YNotebook(YBaseDoc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ymeta = self._ydoc.get_map("meta")
        self._ycells = self._ydoc.get_array("cells")

    def get_cell(self, index: int) -> Dict[str, Any]:
        meta = self._ymeta.to_json()
        cell = self._ycells[index].to_json()
        cast_all(cell, float, int)  # cells coming from Yjs have e.g. execution_count as float
        if "id" in cell and meta["nbformat"] == 4 and meta["nbformat_minor"] <= 4:
            # strip cell IDs if we have notebook format 4.0-4.4
            del cell["id"]
        if (
            "attachments" in cell
            and cell["cell_type"] in ("raw", "markdown")
            and not cell["attachments"]
        ):
            del cell["attachments"]
        return cell

    def append_cell(self, value: Dict[str, Any], txn=None) -> None:
        ycell = self.create_ycell(value)
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.append(txn, ycell)
        else:
            self._ycells.append(txn, ycell)

    def set_cell(self, index: int, value: Dict[str, Any], txn=None) -> None:
        ycell = self.create_ycell(value)
        self.set_ycell(index, ycell, txn)

    def create_ycell(self, value: Dict[str, Any]) -> None:
        cell = copy.deepcopy(value)
        if "id" not in cell:
            cell["id"] = str(uuid4())
        cell_type = cell["cell_type"]
        cell["source"] = Y.YText(cell["source"])
        cell["metadata"] = cell.get("metadata", {})

        if cell_type in ("raw", "markdown"):
            if "attachments" in cell and not cell["attachments"]:
                del cell["attachments"]
        elif cell_type == "code":
            cell["outputs"] = Y.YArray(cell.get("outputs", []))

        return Y.YMap(cell)

    def set_ycell(self, index: int, ycell: Y.YMap, txn=None):
        if txn is None:
            with self._ydoc.begin_transaction() as txn:
                self._ycells.delete(txn, index)
                self._ycells.insert(txn, index, ycell)
        else:
            self._ycells.delete(txn, index)
            self._ycells.insert(txn, index, ycell)

    def get(self):
        meta = self._ymeta.to_json()
        cast_all(meta, float, int)  # notebook coming from Yjs has e.g. nbformat as float
        cells = []
        for i in range(len(self._ycells)):
            cell = self.get_cell(i)
            if "id" in cell and meta["nbformat"] == 4 and meta["nbformat_minor"] <= 4:
                # strip cell IDs if we have notebook format 4.0-4.4
                del cell["id"]
            if (
                "attachments" in cell
                and cell["cell_type"] in ["raw", "markdown"]
                and not cell["attachments"]
            ):
                del cell["attachments"]
            cells.append(cell)

        return dict(
            cells=cells,
            metadata=meta.get("metadata", {}),
            nbformat=int(meta.get("nbformat", 0)),
            nbformat_minor=int(meta.get("nbformat_minor", 0)),
        )

    def set(self, value):
        nb_without_cells = {key: value[key] for key in value.keys() if key != "cells"}
        nb = copy.deepcopy(nb_without_cells)
        cast_all(nb, int, float)  # Yjs expects numbers to be floating numbers
        cells = value["cells"] or [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": "",
                "id": str(uuid4()),
            }
        ]

        with self._ydoc.begin_transaction() as t:
            # clear document
            cells_len = len(self._ycells)
            for key in self._ymeta:
                self._ymeta.pop(t, key)
            if cells_len:
                self._ycells.delete_range(t, 0, cells_len)
            for key in [k for k in self._ystate if k not in ("dirty", "path")]:
                self._ystate.pop(t, key)

            # initialize document
            self._ycells.extend(t, [self.create_ycell(cell) for cell in cells])
            self._ymeta.set(t, "metadata", nb["metadata"])
            self._ymeta.set(t, "nbformat", nb["nbformat"])
            self._ymeta.set(t, "nbformat_minor", nb["nbformat_minor"])

    def observe(self, callback):
        self.unobserve()
        self._subscriptions[self._ystate] = self._ystate.observe(callback)
        self._subscriptions[self._ymeta] = self._ymeta.observe(callback)
        self._subscriptions[self._ycells] = self._ycells.observe_deep(callback)
