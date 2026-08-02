#!/usr/bin/env python3
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QProgressBar, QMessageBox, QStatusBar,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QIcon

LOGO = Path(__file__).parent / "assets" / "Logo.png"

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".tiff", ".tif", ".ico", ".pbm", ".pgm", ".ppm",
}


class ScanWorker(QObject):
    file_found = pyqtSignal(str, str, str)  # path, name, error
    progress = pyqtSignal(int, int)          # current, total
    finished = pyqtSignal()

    def __init__(self, folder: str, recursive: bool):
        super().__init__()
        self.folder = folder
        self.recursive = recursive
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            root = Path(self.folder)
            all_items = list(root.rglob("*") if self.recursive else root.iterdir())
            image_files = [
                p for p in all_items
                if (p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
                or (p.is_symlink() and not p.exists() and p.suffix.lower() in IMAGE_EXTENSIONS)
            ]
            total = len(image_files)

            for i, path in enumerate(image_files):
                if self._stop:
                    break
                self.progress.emit(i + 1, total)
                error = self._check_image(path)
                if error:
                    self.file_found.emit(str(path), path.name, error)
        finally:
            self.finished.emit()

    def _check_image(self, path: Path) -> str | None:
        # Broken symlink
        if path.is_symlink() and not path.exists():
            return f"Broken symlink → {os.readlink(path)}"

        # OS-level read check
        try:
            with open(path, "rb") as f:
                f.read(4096)
        except PermissionError:
            return "Permission denied"
        except OSError as e:
            return f"I/O Error: {e.strerror}"

        # Zero-byte file
        if path.stat().st_size == 0:
            return "Empty file (0 bytes)"

        # Decode check using Qt's own image loader — catches the same
        # errors that Qt image viewers (Gwenview, etc.) report
        img = QImage()
        if not img.load(str(path)) or img.isNull():
            return "Corrupted image: failed to decode"

        return None


class ImgGoneApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImgGone — Corrupted Image Cleaner")
        self.setMinimumSize(860, 560)
        self._folder: str | None = None
        self._worker: ScanWorker | None = None
        self._thread: QThread | None = None
        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Folder row
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color: #888; font-style: italic;")
        folder_row.addWidget(self.folder_label, 1)

        self.recursive_chk = QCheckBox("Include subfolders")
        folder_row.addWidget(self.recursive_chk)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse)
        folder_row.addWidget(self.browse_btn)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._toggle_scan)
        folder_row.addWidget(self.scan_btn)

        layout.addLayout(folder_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["File Name", "Path", "Error"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Bottom row
        bottom = QHBoxLayout()

        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(self.table.selectAll)
        bottom.addWidget(sel_all)

        desel = QPushButton("Deselect All")
        desel.clicked.connect(self.table.clearSelection)
        bottom.addWidget(desel)

        bottom.addStretch()

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 6px 18px;"
        )
        self.delete_btn.clicked.connect(self._delete_selected)
        bottom.addWidget(self.delete_btn)

        layout.addLayout(bottom)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready. Pick a folder and click Scan.")

    # ------------------------------------------------------------ Slots ------

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self._folder = folder
            self.folder_label.setText(folder)
            self.folder_label.setStyleSheet("")
            self.scan_btn.setEnabled(True)
            self.status.showMessage(f"Folder: {folder}")

    def _toggle_scan(self):
        if self._thread and self._thread.isRunning():
            self._worker.stop()
            self.scan_btn.setText("Scan")
            self.status.showMessage("Scan stopped.")
            return

        self.table.setRowCount(0)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.scan_btn.setText("Stop")
        self.status.showMessage("Scanning images…")

        self._worker = ScanWorker(self._folder, self.recursive_chk.isChecked())
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.file_found.connect(self._on_file_found)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(self._thread.quit)

        self._thread.start()

    def _on_file_found(self, path: str, name: str, error: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, path)

        path_item = QTableWidgetItem(path)
        error_item = QTableWidgetItem(error)
        error_item.setForeground(QColor("#e74c3c"))

        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, path_item)
        self.table.setItem(row, 2, error_item)

    def _on_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.progress.setFormat(f"{current} / {total} images")

    def _on_done(self):
        count = self.table.rowCount()
        self.scan_btn.setText("Scan")
        self.progress.setVisible(False)
        self.status.showMessage(
            "Scan complete — all images are healthy."
            if count == 0
            else f"Scan complete — {count} corrupted image(s) found."
        )

    def _delete_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        if not rows:
            QMessageBox.information(self, "Nothing selected", "Select images to delete first.")
            return

        paths = [(row, self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)) for row in rows]

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Permanently delete {len(paths)} image(s)?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        failed = []
        deleted = []
        for row, path in paths:
            try:
                os.remove(path)
                deleted.append(row)
            except Exception as e:
                failed.append(f"{path}:\n  {e}")

        for row in sorted(deleted, reverse=True):
            self.table.removeRow(row)

        if failed:
            QMessageBox.warning(
                self,
                "Some Deletions Failed",
                f"Deleted {len(deleted)} image(s).\n\nFailed:\n" + "\n".join(failed),
            )
        else:
            self.status.showMessage(f"Deleted {len(deleted)} image(s).")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ImgGone")
    if LOGO.exists():
        app.setWindowIcon(QIcon(str(LOGO)))
    window = ImgGoneApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
