import sys
import json
import os
import csv
import pyperclip
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox, QAction, 
    QFileDialog, QStatusBar, QToolBar, QLabel, QDialog, QFormLayout, 
    QComboBox, QAbstractItemView, QShortcut, QCheckBox, QSpinBox, QMainWindow, 
    QProgressBar, QColorDialog, QGroupBox, QTabWidget, QFrame
)
from PyQt5.QtGui import QColor, QBrush, QIcon, QKeySequence, QPainter, QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import qdarkstyle
from plyer import notification
import requests
from settings import load_settings, save_settings, DEFAULT_SETTINGS
from help import HelpWindow
from about import AboutDialog

class AuditLog:
    def __init__(self, filename="audit_log.txt"):
        self.filename = filename

    def log(self, action, item):
        with open(self.filename, "a") as f:
            f.write(f"{datetime.now()}: {action} - {json.dumps(item)}\n")

audit_log = AuditLog()

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    eta = pyqtSignal(str)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, url, output):
        super().__init__()
        self.url = url
        self.output = output

    def run(self):
        response = requests.get(self.url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = datetime.now()

        if total_size == 0:
            self.status.emit("Error: Total size is zero.")
            self.finished.emit(False)
            return

        with open(self.output, 'wb') as f:
            for data in response.iter_content(1024):
                f.write(data)
                downloaded_size += len(data)
                elapsed_time = (datetime.now() - start_time).total_seconds()
                speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                eta = (total_size - downloaded_size) / speed if speed > 0 else 0
                self.progress.emit(int(downloaded_size / total_size * 100))
                self.eta.emit(f"ETA: {int(eta)} seconds")
                self.status.emit(f"Downloaded {downloaded_size} of {total_size} bytes")

        self.finished.emit(True)

class UpdateCheckThread(QThread):
    update_available = pyqtSignal(bool, str, str)

    def run(self):
        # Update the URL to fetch the raw version.txt content directly
        version_url = "https://raw.githubusercontent.com/skillerious/Starfield-IDDB/main/version.txt"
        try:
            response = requests.get(version_url)
            if response.status_code == 200:
                latest_version = response.text.strip()  # Get and strip the content of version.txt
                current_version = "1.0"  # Update this to reflect the current app version.

                # Debugging statement to check fetched versions
                print(f"Fetched version: {latest_version}, Current version: {current_version}")

                if latest_version > current_version:
                    # Assuming there's a corresponding executable for the new version
                    exe_url = f"https://github.com/skillerious/Starfield-IDDB/releases/download/{latest_version}/StarfieldIDDB-{latest_version}.exe"
                    self.update_available.emit(True, latest_version, exe_url)
                else:
                    self.update_available.emit(False, current_version, "")
            else:
                print(f"Failed to fetch version.txt, status code: {response.status_code}")
                self.update_available.emit(False, "", "")
        except requests.RequestException as e:
            print(f"Request failed: {str(e)}")
            self.update_available.emit(False, "", str(e))

            # In the main window class (or wherever this is used):
def on_update_check_complete(self, update_available, latest_version, exe_url):
    if update_available:
        reply = QMessageBox.question(
            self,
            'Update Available',
            f"A new version ({latest_version}) is available. Do you want to update?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            update_dialog = UpdateDialog(exe_url, self)
            update_dialog.exec_()
        else:
            self.status_bar.showMessage("Update postponed.")
    else:
        if latest_version:
            QMessageBox.information(self, "No Update", f"You are using the latest version ({latest_version}).")
        else:
            QMessageBox.warning(self, "Update Check Failed", "Failed to check for updates.")

    self.status_bar.showMessage("Ready")

class UpdateDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.setWindowTitle("Downloading Update")
        self.setGeometry(100, 100, 400, 200)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Starting download...", self)
        self.layout.addWidget(self.status_label)

        self.eta_label = QLabel("", self)
        self.layout.addWidget(self.eta_label)

        self.download_thread = DownloadThread(self.url, "update.exe")
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.eta.connect(self.eta_label.setText)
        self.download_thread.status.connect(self.status_label.setText)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()

    def download_finished(self, success):
        if success:
            self.status_label.setText("Download completed.")
            self.eta_label.setText("")
            QMessageBox.information(self, "Update", "Download completed successfully. Please restart the application to apply the update.")
        else:
            self.status_label.setText("Download failed.")
            self.eta_label.setText("")

class JSONViewerApp(QMainWindow):
    def __init__(self, json_files):
        super().__init__()
        self.json_files = json_files
        self.file_map = {
            "Favourites": "Favourites.json",
            "Popular Items": "PopularItems.json",
            "Weapons": "weapons.json",
            "Ammo": "ammo.json",
            "Space Suits": "spacesuits.json",
            "Helmets": "helmets.json",
            "Boost Packs": "Boostpacks.json",
            "Aid": "aid.json",
            "Food": "food.json",
            "Skill Books": "book.json",
            "Skills": "skills.json",
            "Traits": "traits.json",
            "Materials/Resources": "materials.json",
            "Clothing": "clothing.json"
        }
        self.current_file = None
        self.data = []
        self.undo_stack = []
        self.redo_stack = []
        self.settings = load_settings()
        self.buttons = {}
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Starfield IDDB')
        self.setGeometry(100, 100, 1200, 600)
        self.setWindowIcon(QIcon('images/starfield.png'))

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        toolbar = QToolBar(self)
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self.settings.get('toolbar_bg_start', '#3a3a3a')}, stop:1 {self.settings.get('toolbar_bg_end', '#1e1e1e')});
                border-bottom: 1px solid {self.settings.get('highlight_color', '#3a7ae0')};
                spacing: 10px;
                padding: 5px;
            }}
            QToolButton {{
                color: {self.settings.get('font_color', 'white')};
                font-size: 12pt;
                padding: 5px;
                background: transparent;
                border: none;
            }}
            QToolButton:hover {{
                background: {self.settings.get('button_hover_color', '#3a7ae0')};
                border-radius: 5px;
            }}
            QToolButton:pressed {{
                background: {self.settings.get('button_press_color', '#2a69bf')};
                border-radius: 5px;
            }}
        """)

        new_file_action = QAction(QIcon('images/new.png'), 'New File', self)
        new_file_action.triggered.connect(self.new_file)
        toolbar.addAction(new_file_action)

        add_action = QAction(QIcon('images/add.png'), 'Add', self)
        add_action.triggered.connect(self.add_item)
        toolbar.addAction(add_action)

        edit_action = QAction(QIcon('images/edit.png'), 'Edit', self)
        edit_action.triggered.connect(self.edit_selected_item)
        toolbar.addAction(edit_action)

        open_action = QAction(QIcon('images/open.png'), 'Open', self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        save_action = QAction(QIcon('images/save.png'), 'Save', self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        save_as_action = QAction(QIcon('images/save_as.png'), 'Save As', self)
        save_as_action.triggered.connect(self.save_file_as)
        toolbar.addAction(save_as_action)

        toolbar.addSeparator()

        print_action = QAction(QIcon('images/print.png'), 'Print', self)
        print_action.triggered.connect(self.print_file)
        toolbar.addAction(print_action)

        toolbar.addSeparator()

        export_csv_action = QAction(QIcon('images/export_csv.png'), 'Export to CSV', self)
        export_csv_action.triggered.connect(self.export_to_csv)
        toolbar.addAction(export_csv_action)

        export_pdf_action = QAction(QIcon('images/pdf.png'), 'Export to PDF', self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        toolbar.addAction(export_pdf_action)

        export_json_action = QAction(QIcon('images/export_json.png'), 'Export to JSON', self)
        export_json_action.triggered.connect(self.export_to_json)
        toolbar.addAction(export_json_action)

        toolbar.addSeparator()

        undo_action = QAction(QIcon('images/undo.png'), 'Undo', self)
        undo_action.setShortcut('Ctrl+Shift+Z')
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)

        redo_action = QAction(QIcon('images/redo.png'), 'Redo', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        refresh_action = QAction(QIcon('images/refresh.png'), 'Refresh', self)
        refresh_action.triggered.connect(self.refresh)
        toolbar.addAction(refresh_action)

        delete_action = QAction(QIcon('images/delete.png'), 'Delete', self)
        delete_action.triggered.connect(self.delete_selected_items)
        toolbar.addAction(delete_action)

        toolbar.addSeparator()

        settings_action = QAction(QIcon('images/settings.png'), 'Settings', self)
        settings_action.triggered.connect(self.open_settings_dialog)
        toolbar.addAction(settings_action)

        help_action = QAction(QIcon('images/help.png'), 'Help', self)
        help_action.triggered.connect(self.show_help_dialog)
        toolbar.addAction(help_action)

        about_action = QAction(QIcon('images/about.png'), 'About', self)
        about_action.triggered.connect(self.show_about_dialog)
        toolbar.addAction(about_action)

        self.addToolBar(toolbar)

        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit(self)
        self.search_entry.setPlaceholderText('Search...')
        self.search_entry.textChanged.connect(self.schedule_search)
        search_layout.addWidget(self.search_entry)
        
        self.clear_button = QPushButton('Clear', self)
        self.clear_button.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_button)

        self.advanced_search_button = QPushButton('Advanced Search', self)
        self.advanced_search_button.clicked.connect(self.open_advanced_search_dialog)
        search_layout.addWidget(self.advanced_search_button)
        
        main_layout.addLayout(search_layout)

        buttons_layout = QHBoxLayout()
        for display_name in self.file_map:
            button = QPushButton(display_name, self)
            button.setFixedHeight(40)
            button.setStyleSheet(f"""
                QPushButton {{
                    padding: 10px;
                    font-size: 12pt;
                    border: 2px solid {self.settings.get('highlight_color', '#3a7ae0')};
                    color: {self.settings.get('font_color', 'white')};
                    background-color: transparent;
                }}
                QPushButton:checked {{
                    background-color: {self.settings.get('highlight_color', '#3a7ae0')};
                }}
            """)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, f=display_name: self.load_json_with_indicator(f))
            self.buttons[display_name] = button
            buttons_layout.addWidget(button)
        
        main_layout.addLayout(buttons_layout)

        stacked_layout = QVBoxLayout()

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Item ID', 'Item Name', 'Console Command', 'Favourite'])
        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {self.settings.get('highlight_color', '#3a7ae0')};
                color: {self.settings.get('font_color', 'white')};
                font-weight: bold;
                font-size: {self.settings.get('font_size', 12)}pt;
                padding: 5px;
                border: 1px solid {self.settings.get('highlight_color', '#3a7ae0')};
            }}
        """)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {self.settings.get('highlight_color', '#3a7ae0')};
                font-size: {self.settings.get('font_size', 14)}pt;
                alternate-background-color: {self.settings.get('alternate_background_color', '#2e2e2e')};
                background-color: {self.settings.get('background_color', '#1e1e1e')};
                color: {self.settings.get('font_color', 'white')};
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {self.settings.get('highlight_color', '#3a7ae0')};
                padding: 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.settings.get('highlight_color', '#5a9ae0')};
                color: white;
            }}
        """)
        self.table.setAlternatingRowColors(self.settings["alternate_row_colors"])
        self.table.setShowGrid(self.settings["show_grid"])
        self.table.cellClicked.connect(self.handle_cell_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.show_item_details)

        stacked_layout.addWidget(self.table)

        main_layout.addLayout(stacked_layout)

        self.detail_view = QLabel("Select an item to view details", self)
        self.detail_view.setStyleSheet(f"color: {self.settings.get('font_color', 'white')}; padding: 10px; font-size: {self.settings.get('font_size', 12)}pt;")
        main_layout.addWidget(self.detail_view)

        self.status_bar = QStatusBar(self)
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)
        
        self.setCentralWidget(main_widget)
        self.apply_theme()
        self.setup_shortcuts()
        self.load_startup_json()
        self.highlight_active_button()

        self.showMaximized()

    def load_json_with_indicator(self, display_name):
        self.load_json(self.file_map[display_name])
        self.update_button_styles(display_name)

    def update_button_styles(self, active_button_name):
        for name, button in self.buttons.items():
            button.setChecked(name == active_button_name)

    def load_startup_json(self):
        if self.settings.get("startup_json") == "Custom":
            if self.settings.get("custom_json_path"):
                self.load_json(self.settings["custom_json_path"])
        else:
            self.load_json(self.file_map.get(self.settings.get("startup_json", "Favourites")))

    def highlight_active_button(self):
        startup_json_name = self.settings.get("startup_json", "Favourites")
        if startup_json_name == "Custom":
            custom_path = self.settings.get("custom_json_path", "")
            if custom_path:
                for name, path in self.file_map.items():
                    if path == custom_path:
                        startup_json_name = name
                        break
        self.update_button_styles(startup_json_name)

    def load_json(self, filename):
        self.current_file = filename
        self.status_bar.showMessage(f"Loading {filename}")
        filepath = os.path.join(os.getcwd(), filename) if filename in self.file_map.values() else filename
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f)
        with open(filepath, "r") as f:
            try:
                self.data = json.load(f)
            except json.JSONDecodeError:
                self.data = []
        self.populate_listbox(self.data)
        self.detail_view.setText("Select an item to view details")
        self.status_bar.showMessage(f"Loaded {filename} - {len(self.data)} items")

    def populate_listbox(self, data):
        self.table.setRowCount(0)
        for index, item in enumerate(data):
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(self.table.rowCount() - 1, 0, QTableWidgetItem(item.get("Item Code", "")))
            self.table.setItem(self.table.rowCount() - 1, 1, QTableWidgetItem(item.get("Item Name", "")))

            cell_widget = QWidget()
            cell_layout = QHBoxLayout()
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(10)

            console_command_label = QLabel(item.get("Console Command", ""))
            console_command_label.setStyleSheet(f"color: {self.settings.get('font_color', 'white')}; background: transparent; font-size: {self.settings.get('font_size', 14)}pt;")
            cell_layout.addWidget(console_command_label, stretch=1)

            copy_button = QPushButton('Copy')
            copy_button.setStyleSheet(f"background: transparent; color: {self.settings.get('font_color', 'white')}; font-size: {self.settings.get('font_size', 12)}pt; border: none;")
            copy_button.setFixedSize(50, 28)
            copy_button.clicked.connect(lambda ch, cmd=item.get("Console Command", ""): self.copy_command(cmd))
            cell_layout.addWidget(copy_button, stretch=0)

            cell_widget.setLayout(cell_layout)
            cell_widget.setStyleSheet("background: transparent;")
            self.table.setCellWidget(self.table.rowCount() - 1, 2, cell_widget)

            fav_item = QTableWidgetItem()
            fav_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(self.table.rowCount() - 1, 3, fav_item)

            self.table.setRowHeight(self.table.rowCount() - 1, self.settings["row_height"])

            background_color = QBrush(QColor(self.settings.get('alternate_background_color', '#2e2e2e'))) if index % 2 == 0 else QBrush(QColor(self.settings.get('background_color', '#1e1e1e')))
            for col in range(3):
                cell = self.table.item(index, col)
                if cell:
                    cell.setBackground(background_color)

    def schedule_search(self):
        self.search_timer.start(300)

    def perform_search(self):
        search_term = self.search_entry.text().lower()
        filtered_data = [item for item in self.data if search_term in item.get("Item Code", "").lower() or search_term in item.get("Item Name", "").lower() or search_term in item.get("Console Command", "").lower()]
        self.populate_listbox(filtered_data)
        self.detail_view.setText("Select an item to view details")

    def open_advanced_search_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced Search")
        layout = QFormLayout()
        search_term_edit = QLineEdit()
        layout.addRow("Search Term:", search_term_edit)

        self.search_in_item_code = QCheckBox("Search in Item Code")
        self.search_in_item_code.setChecked(True)
        self.search_in_item_name = QCheckBox("Search in Item Name")
        self.search_in_item_name.setChecked(True)
        self.search_in_console_command = QCheckBox("Search in Console Command")
        self.search_in_console_command.setChecked(True)
        layout.addRow(self.search_in_item_code)
        layout.addRow(self.search_in_item_name)
        layout.addRow(self.search_in_console_command)

        search_button = QPushButton("Search")
        search_button.clicked.connect(lambda: self.perform_advanced_search(dialog, search_term_edit.text()))
        layout.addWidget(search_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def perform_advanced_search(self, dialog, search_term):
        search_term = search_term.lower()
        filtered_data = []

        for item in self.data:
            if (
                (self.search_in_item_code.isChecked() and search_term in item.get("Item Code", "").lower()) or
                (self.search_in_item_name.isChecked() and search_term in item.get("Item Name", "").lower()) or
                (self.search_in_console_command.isChecked() and search_term in item.get("Console Command", "").lower())
            ):
                filtered_data.append(item)

        self.populate_listbox(filtered_data)
        self.detail_view.setText("Select an item to view details")
        dialog.accept()

    def clear_search(self):
        self.search_entry.clear()
        self.populate_listbox(self.data)
        self.detail_view.setText("Select an item to view details")

    def handle_cell_click(self, row, column):
        self.update_detail_view(row)

    def update_detail_view(self, row):
        item_code = self.table.item(row, 0).text()
        item_name = self.table.item(row, 1).text()
        console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
        details = f"Item Code: {item_code}\nItem Name: {item_name}\nConsole Command: {console_command}"
        self.detail_view.setText(details)

    def show_item_details(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            self.update_detail_view(selected_row)
        else:
            self.detail_view.setText("Select an item to view details")

    def copy_command(self, command):
        pyperclip.copy(command)
        icon_path = os.path.join(os.getcwd(), 'images', 'starfield.png')
        notification.notify(
            title='Starfield IDDB',
            message='Console command copied to clipboard',
            app_name='Starfield IDDB',
            app_icon=icon_path
        )

    def open_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return

        row = self.table.indexAt(position).row()
        item_code = self.table.item(row, 0).text()
        item_name = self.table.item(row, 1).text()
        console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
        item = {
            "Item Code": item_code,
            "Item Name": item_name,
            "Console Command": console_command
        }

        context_menu = QMenu()

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.copy_command(item.get("Console Command", "")))
        context_menu.addAction(copy_action)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.edit_item_from_menu(position))
        context_menu.addAction(edit_action)

        context_menu.exec_(self.table.viewport().mapToGlobal(position))

    def edit_item_from_menu(self, position):
        row = self.table.indexAt(position).row()
        item_code = self.table.item(row, 0).text()
        item_name = self.table.item(row, 1).text()
        console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Item")
        layout = QFormLayout()
        item_code_edit = QLineEdit(item_code)
        item_name_edit = QLineEdit(item_name)
        console_command_edit = QLineEdit(console_command)
        layout.addRow("Item Code:", item_code_edit)
        layout.addRow("Item Name:", item_name_edit)
        layout.addRow("Console Command:", console_command_edit)
        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_edit(dialog, row, item_code_edit, item_name_edit, console_command_edit))
        layout.addWidget(save_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_edit(self, dialog, row, item_code_edit, item_name_edit, console_command_edit):
        self.table.setItem(row, 0, QTableWidgetItem(item_code_edit.text()))
        self.table.setItem(row, 1, QTableWidgetItem(item_name_edit.text()))
        cell_widget = self.table.cellWidget(row, 2)
        cell_widget.layout().itemAt(0).widget().setText(console_command_edit.text())

        self.data[row] = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text()
        }

        with open(self.current_file, 'w') as jsonfile:
            json.dump(self.data, jsonfile)

        dialog.accept()

    def export_to_csv(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", self.settings.get("default_csv_path", ""), "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Item ID', 'Item Name', 'Console Command', 'Favourite'])
                for row in range(self.table.rowCount()):
                    writer.writerow([
                        self.table.item(row, 0).text(), 
                        self.table.item(row, 1).text(), 
                        self.table.cellWidget(row, 2).layout().itemAt(0).widget().text(), 
                    ])
            self.status_bar.showMessage(f"Data exported to {file_path}")

    def export_to_json(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON", self.settings.get("default_json_path", ""), "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            data_to_export = []
            for row in range(self.table.rowCount()):
                item = {
                    "Item Code": self.table.item(row, 0).text(),
                    "Item Name": self.table.item(row, 1).text(),
                    "Console Command": self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
                }
                data_to_export.append(item)
            with open(file_path, 'w') as jsonfile:
                json.dump(data_to_export, jsonfile)
            self.status_bar.showMessage(f"Data exported to {file_path}")

    def export_to_pdf(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", self.settings.get("default_json_path", ""), "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            painter = QPainter(printer)
            screen = self.grab()
            screen_scaled = screen.scaled(printer.pageRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (printer.pageRect().width() - screen_scaled.width()) / 2
            y = (printer.pageRect().height() - screen_scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), screen_scaled)
            painter.end()
            self.status_bar.showMessage(f"Data exported to {file_path}")

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON File", self.settings.get("default_json_path", ""), "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            self.load_json(file_path)

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
            return
        with open(self.current_file, 'w') as jsonfile:
            json.dump(self.data, jsonfile)
        self.status_bar.showMessage(f"Data saved to {self.current_file}")

    def save_file_as(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON", self.settings.get("default_json_path", ""), "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            self.current_file = file_path
            self.save_file()

    def new_file(self):
        self.current_file = None
        self.data = []
        self.populate_listbox(self.data)
        self.detail_view.setText("Select an item to view details")
        self.status_bar.showMessage("New file created")

    def refresh(self):
        if self.current_file:
            self.load_json(self.current_file)
        self.status_bar.showMessage("Refreshed")

    def delete_selected_items(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        for row in selected_rows:
            self.table.removeRow(row)
            del self.data[row]
        self.save_file()
        self.status_bar.showMessage("Selected items deleted")

    def print_file(self):
        printer = QPrinter(QPrinter.HighResolution)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            screen = self.grab()
            screen_scaled = screen.scaled(printer.pageRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (printer.pageRect().width() - screen_scaled.width()) / 2
            y = (printer.pageRect().height() - screen_scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), screen_scaled)
            painter.end()
            self.status_bar.showMessage("Printed successfully")

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        main_layout = QVBoxLayout()

        tabs = QTabWidget()

        appearance_widget = QWidget()
        appearance_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.settings["theme"])
        appearance_layout.addRow("Theme:", self.theme_combo)

        self.highlight_color_edit = QLineEdit(self.settings.get("highlight_color", "#3a7ae0"))
        self.highlight_color_canvas = QFrame()
        self.highlight_color_canvas.setFixedSize(20, 20)
        self.highlight_color_canvas.setStyleSheet(f"background-color: {self.settings.get('highlight_color', '#3a7ae0')};")
        self.highlight_color_button = QPushButton()
        self.highlight_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.highlight_color_button.setFixedSize(25, 25)
        self.highlight_color_button.clicked.connect(lambda: self.select_color("highlight_color", self.highlight_color_edit, self.highlight_color_canvas))
        highlight_color_layout = QHBoxLayout()
        highlight_color_layout.addWidget(self.highlight_color_edit)
        highlight_color_layout.addWidget(self.highlight_color_canvas)
        highlight_color_layout.addWidget(self.highlight_color_button)
        appearance_layout.addRow("Highlight Color:", highlight_color_layout)

        self.font_color_edit = QLineEdit(self.settings.get("font_color", "white"))
        self.font_color_canvas = QFrame()
        self.font_color_canvas.setFixedSize(20, 20)
        self.font_color_canvas.setStyleSheet(f"background-color: {self.settings.get('font_color', 'white')};")
        self.font_color_button = QPushButton()
        self.font_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.font_color_button.setFixedSize(25, 25)
        self.font_color_button.clicked.connect(lambda: self.select_color("font_color", self.font_color_edit, self.font_color_canvas))
        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(self.font_color_edit)
        font_color_layout.addWidget(self.font_color_canvas)
        font_color_layout.addWidget(self.font_color_button)
        appearance_layout.addRow("Font Color:", font_color_layout)

        self.background_color_edit = QLineEdit(self.settings.get("background_color", "#1e1e1e"))
        self.background_color_canvas = QFrame()
        self.background_color_canvas.setFixedSize(20, 20)
        self.background_color_canvas.setStyleSheet(f"background-color: {self.settings.get('background_color', '#1e1e1e')};")
        self.background_color_button = QPushButton()
        self.background_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.background_color_button.setFixedSize(25, 25)
        self.background_color_button.clicked.connect(lambda: self.select_color("background_color", self.background_color_edit, self.background_color_canvas))
        background_color_layout = QHBoxLayout()
        background_color_layout.addWidget(self.background_color_edit)
        background_color_layout.addWidget(self.background_color_canvas)
        background_color_layout.addWidget(self.background_color_button)
        appearance_layout.addRow("Background Color:", background_color_layout)

        self.alternate_background_color_edit = QLineEdit(self.settings.get("alternate_background_color", "#2e2e2e"))
        self.alternate_background_color_canvas = QFrame()
        self.alternate_background_color_canvas.setFixedSize(20, 20)
        self.alternate_background_color_canvas.setStyleSheet(f"background-color: {self.settings.get('alternate_background_color', '#2e2e2e')};")
        self.alternate_background_color_button = QPushButton()
        self.alternate_background_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.alternate_background_color_button.setFixedSize(25, 25)
        self.alternate_background_color_button.clicked.connect(lambda: self.select_color("alternate_background_color", self.alternate_background_color_edit, self.alternate_background_color_canvas))
        alternate_background_color_layout = QHBoxLayout()
        alternate_background_color_layout.addWidget(self.alternate_background_color_edit)
        alternate_background_color_layout.addWidget(self.alternate_background_color_canvas)
        alternate_background_color_layout.addWidget(self.alternate_background_color_button)
        appearance_layout.addRow("Alternate Background Color:", alternate_background_color_layout)

        self.border_color_edit = QLineEdit(self.settings.get("border_color", "#3a7ae0"))
        self.border_color_canvas = QFrame()
        self.border_color_canvas.setFixedSize(20, 20)
        self.border_color_canvas.setStyleSheet(f"background-color: {self.settings.get('border_color', '#3a7ae0')};")
        self.border_color_button = QPushButton()
        self.border_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.border_color_button.setFixedSize(25, 25)
        self.border_color_button.clicked.connect(lambda: self.select_color("border_color", self.border_color_edit, self.border_color_canvas))
        border_color_layout = QHBoxLayout()
        border_color_layout.addWidget(self.border_color_edit)
        border_color_layout.addWidget(self.border_color_canvas)
        border_color_layout.addWidget(self.border_color_button)
        appearance_layout.addRow("Border Color:", border_color_layout)

        self.button_hover_color_edit = QLineEdit(self.settings.get("button_hover_color", "#3a7ae0"))
        self.button_hover_color_canvas = QFrame()
        self.button_hover_color_canvas.setFixedSize(20, 20)
        self.button_hover_color_canvas.setStyleSheet(f"background-color: {self.settings.get('button_hover_color', '#3a7ae0')};")
        self.button_hover_color_button = QPushButton()
        self.button_hover_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.button_hover_color_button.setFixedSize(25, 25)
        self.button_hover_color_button.clicked.connect(lambda: self.select_color("button_hover_color", self.button_hover_color_edit, self.button_hover_color_canvas))
        button_hover_color_layout = QHBoxLayout()
        button_hover_color_layout.addWidget(self.button_hover_color_edit)
        button_hover_color_layout.addWidget(self.button_hover_color_canvas)
        button_hover_color_layout.addWidget(self.button_hover_color_button)
        appearance_layout.addRow("Button Hover Color:", button_hover_color_layout)

        self.button_press_color_edit = QLineEdit(self.settings.get("button_press_color", "#2a69bf"))
        self.button_press_color_canvas = QFrame()
        self.button_press_color_canvas.setFixedSize(20, 20)
        self.button_press_color_canvas.setStyleSheet(f"background-color: {self.settings.get('button_press_color', '#2a69bf')};")
        self.button_press_color_button = QPushButton()
        self.button_press_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.button_press_color_button.setFixedSize(25, 25)
        self.button_press_color_button.clicked.connect(lambda: self.select_color("button_press_color", self.button_press_color_edit, self.button_press_color_canvas))
        button_press_color_layout = QHBoxLayout()
        button_press_color_layout.addWidget(self.button_press_color_edit)
        button_press_color_layout.addWidget(self.button_press_color_canvas)
        button_press_color_layout.addWidget(self.button_press_color_button)
        appearance_layout.addRow("Button Press Color:", button_press_color_layout)

        self.toolbar_bg_start_edit = QLineEdit(self.settings.get("toolbar_bg_start", "#3a3a3a"))
        self.toolbar_bg_start_canvas = QFrame()
        self.toolbar_bg_start_canvas.setFixedSize(20, 20)
        self.toolbar_bg_start_canvas.setStyleSheet(f"background-color: {self.settings.get('toolbar_bg_start', '#3a3a3a')};")
        self.toolbar_bg_start_button = QPushButton()
        self.toolbar_bg_start_button.setIcon(QIcon("images/colorpicker.png"))
        self.toolbar_bg_start_button.setFixedSize(25, 25)
        self.toolbar_bg_start_button.clicked.connect(lambda: self.select_color("toolbar_bg_start", self.toolbar_bg_start_edit, self.toolbar_bg_start_canvas))
        toolbar_bg_start_layout = QHBoxLayout()
        toolbar_bg_start_layout.addWidget(self.toolbar_bg_start_edit)
        toolbar_bg_start_layout.addWidget(self.toolbar_bg_start_canvas)
        toolbar_bg_start_layout.addWidget(self.toolbar_bg_start_button)
        appearance_layout.addRow("Toolbar BG Start:", toolbar_bg_start_layout)

        self.toolbar_bg_end_edit = QLineEdit(self.settings.get("toolbar_bg_end", "#1e1e1e"))
        self.toolbar_bg_end_canvas = QFrame()
        self.toolbar_bg_end_canvas.setFixedSize(20, 20)
        self.toolbar_bg_end_canvas.setStyleSheet(f"background-color: {self.settings.get('toolbar_bg_end', '#1e1e1e')};")
        self.toolbar_bg_end_button = QPushButton()
        self.toolbar_bg_end_button.setIcon(QIcon("images/colorpicker.png"))
        self.toolbar_bg_end_button.setFixedSize(25, 25)
        self.toolbar_bg_end_button.clicked.connect(lambda: self.select_color("toolbar_bg_end", self.toolbar_bg_end_edit, self.toolbar_bg_end_canvas))
        toolbar_bg_end_layout = QHBoxLayout()
        toolbar_bg_end_layout.addWidget(self.toolbar_bg_end_edit)
        toolbar_bg_end_layout.addWidget(self.toolbar_bg_end_canvas)
        toolbar_bg_end_layout.addWidget(self.toolbar_bg_end_button)
        appearance_layout.addRow("Toolbar BG End:", toolbar_bg_end_layout)

        self.dialog_bg_color_edit = QLineEdit(self.settings.get("dialog_bg_color", "#1e1e1e"))
        self.dialog_bg_color_canvas = QFrame()
        self.dialog_bg_color_canvas.setFixedSize(20, 20)
        self.dialog_bg_color_canvas.setStyleSheet(f"background-color: {self.settings.get('dialog_bg_color', '#1e1e1e')};")
        self.dialog_bg_color_button = QPushButton()
        self.dialog_bg_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.dialog_bg_color_button.setFixedSize(25, 25)
        self.dialog_bg_color_button.clicked.connect(lambda: self.select_color("dialog_bg_color", self.dialog_bg_color_edit, self.dialog_bg_color_canvas))
        dialog_bg_color_layout = QHBoxLayout()
        dialog_bg_color_layout.addWidget(self.dialog_bg_color_edit)
        dialog_bg_color_layout.addWidget(self.dialog_bg_color_canvas)
        dialog_bg_color_layout.addWidget(self.dialog_bg_color_button)
        appearance_layout.addRow("Dialog BG Color:", dialog_bg_color_layout)

        self.label_color_edit = QLineEdit(self.settings.get("label_color", "white"))
        self.label_color_canvas = QFrame()
        self.label_color_canvas.setFixedSize(20, 20)
        self.label_color_canvas.setStyleSheet(f"background-color: {self.settings.get('label_color', 'white')};")
        self.label_color_button = QPushButton()
        self.label_color_button.setIcon(QIcon("images/colorpicker.png"))
        self.label_color_button.setFixedSize(25, 25)
        self.label_color_button.clicked.connect(lambda: self.select_color("label_color", self.label_color_edit, self.label_color_canvas))
        label_color_layout = QHBoxLayout()
        label_color_layout.addWidget(self.label_color_edit)
        label_color_layout.addWidget(self.label_color_canvas)
        label_color_layout.addWidget(self.label_color_button)
        appearance_layout.addRow("Label Color:", label_color_layout)

        restore_colors_button = QPushButton("Restore Default Colors")
        restore_colors_button.clicked.connect(self.restore_default_colors)
        appearance_layout.addWidget(restore_colors_button)

        self.color_palette_combo = QComboBox()
        self.color_palette_combo.addItems(["Default", "Cool Blues", "Warm Sunset", "Forest Greens", "Desert Sands"])
        self.color_palette_combo.currentTextChanged.connect(self.apply_color_palette)
        appearance_layout.addRow("Color Palette:", self.color_palette_combo)

        appearance_widget.setLayout(appearance_layout)
        tabs.addTab(appearance_widget, "Appearance")

        view_widget = QWidget()
        view_layout = QFormLayout()

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 24)
        self.font_size_spinbox.setValue(self.settings.get("font_size", 12))
        view_layout.addRow("Font Size:", self.font_size_spinbox)

        self.row_height_spinbox = QSpinBox()
        self.row_height_spinbox.setRange(20, 100)
        self.row_height_spinbox.setValue(self.settings.get("row_height", 50))
        view_layout.addRow("Row Height:", self.row_height_spinbox)

        self.show_grid_checkbox = QCheckBox("Show Grid")
        self.show_grid_checkbox.setChecked(self.settings.get("show_grid", True))
        view_layout.addRow(self.show_grid_checkbox)

        self.alternate_row_colors_checkbox = QCheckBox("Alternate Row Colors")
        self.alternate_row_colors_checkbox.setChecked(self.settings.get("alternate_row_colors", True))
        view_layout.addRow(self.alternate_row_colors_checkbox)

        view_widget.setLayout(view_layout)
        tabs.addTab(view_widget, "View")

        shortcuts_widget = QWidget()
        shortcuts_layout = QFormLayout()

        self.shortcut_new_file_edit = QLineEdit(self.settings.get("shortcut_new_file", "Ctrl+N"))
        shortcuts_layout.addRow("New File Shortcut:", self.shortcut_new_file_edit)

        self.shortcut_add_edit = QLineEdit(self.settings.get("shortcut_add", "Ctrl+A"))
        shortcuts_layout.addRow("Add Shortcut:", self.shortcut_add_edit)

        self.shortcut_edit_edit = QLineEdit(self.settings.get("shortcut_edit", "Ctrl+E"))
        shortcuts_layout.addRow("Edit Shortcut:", self.shortcut_edit_edit)

        self.shortcut_open_edit = QLineEdit(self.settings.get("shortcut_open", "Ctrl+O"))
        shortcuts_layout.addRow("Open Shortcut:", self.shortcut_open_edit)

        self.shortcut_save_edit = QLineEdit(self.settings.get("shortcut_save", "Ctrl+S"))
        shortcuts_layout.addRow("Save Shortcut:", self.shortcut_save_edit)

        self.shortcut_save_as_edit = QLineEdit(self.settings.get("shortcut_save_as", "Ctrl+Shift+S"))
        shortcuts_layout.addRow("Save As Shortcut:", self.shortcut_save_as_edit)

        self.shortcut_undo_edit = QLineEdit(self.settings.get("shortcut_undo", "Ctrl+Shift+Z"))
        shortcuts_layout.addRow("Undo Shortcut:", self.shortcut_undo_edit)

        self.shortcut_redo_edit = QLineEdit(self.settings.get("shortcut_redo", "Ctrl+Y"))
        shortcuts_layout.addRow("Redo Shortcut:", self.shortcut_redo_edit)

        self.shortcut_delete_edit = QLineEdit(self.settings.get("shortcut_delete", "Delete"))
        shortcuts_layout.addRow("Delete Shortcut:", self.shortcut_delete_edit)

        shortcuts_widget.setLayout(shortcuts_layout)
        tabs.addTab(shortcuts_widget, "Shortcuts")

        defaults_widget = QWidget()
        defaults_layout = QFormLayout()

        self.default_csv_path_edit = QLineEdit(self.settings.get("default_csv_path", ""))
        default_csv_path_button = QPushButton("Browse")
        default_csv_path_button.clicked.connect(self.select_default_csv_path)
        default_csv_path_layout = QHBoxLayout()
        default_csv_path_layout.addWidget(self.default_csv_path_edit)
        default_csv_path_layout.addWidget(default_csv_path_button)
        defaults_layout.addRow("Default CSV Path:", default_csv_path_layout)

        self.default_json_path_edit = QLineEdit(self.settings.get("default_json_path", ""))
        default_json_path_button = QPushButton("Browse")
        default_json_path_button.clicked.connect(self.select_default_json_path)
        default_json_path_layout = QHBoxLayout()
        default_json_path_layout.addWidget(self.default_json_path_edit)
        default_json_path_layout.addWidget(default_json_path_button)
        defaults_layout.addRow("Default JSON Path:", default_json_path_layout)

        self.startup_json_combo = QComboBox()
        self.startup_json_combo.addItems(list(self.file_map.keys()) + ["Custom"])
        self.startup_json_combo.setCurrentText(self.settings["startup_json"])
        defaults_layout.addRow("Startup JSON:", self.startup_json_combo)

        self.custom_json_path_edit = QLineEdit(self.settings.get("custom_json_path", ""))
        self.custom_json_path_button = QPushButton("Browse")
        self.custom_json_path_button.clicked.connect(self.select_custom_json_path)
        custom_json_path_layout = QHBoxLayout()
        custom_json_path_layout.addWidget(self.custom_json_path_edit)
        custom_json_path_layout.addWidget(self.custom_json_path_button)
        defaults_layout.addRow("Custom JSON Path:", custom_json_path_layout)

        self.startup_json_combo.currentTextChanged.connect(self.toggle_custom_json_path)
        self.toggle_custom_json_path(self.startup_json_combo.currentText())

        restore_json_button = QPushButton("Restore JSON from Backup")
        restore_json_button.clicked.connect(self.restore_starfield_json)
        defaults_layout.addRow(restore_json_button)

        defaults_widget.setLayout(defaults_layout)
        tabs.addTab(defaults_widget, "Defaults")

        backup_widget = QWidget()
        backup_layout = QFormLayout()

        self.auto_save_interval_spinbox = QSpinBox()
        self.auto_save_interval_spinbox.setRange(1, 60)
        self.auto_save_interval_spinbox.setValue(self.settings.get("auto_save_interval", 10))
        backup_layout.addRow("Auto Save Interval (minutes):", self.auto_save_interval_spinbox)

        self.enable_notifications_checkbox = QCheckBox("Enable Notifications")
        self.enable_notifications_checkbox.setChecked(self.settings.get("enable_notifications", True))
        backup_layout.addRow(self.enable_notifications_checkbox)

        self.default_export_format_combo = QComboBox()
        self.default_export_format_combo.addItems(["CSV", "JSON", "PDF"])
        self.default_export_format_combo.setCurrentText(self.settings.get("default_export_format", "CSV"))
        backup_layout.addRow("Default Export Format:", self.default_export_format_combo)

        self.backup_frequency_spinbox = QSpinBox()
        self.backup_frequency_spinbox.setRange(1, 60)
        self.backup_frequency_spinbox.setValue(self.settings.get("backup_frequency", 7))
        backup_layout.addRow("Backup Frequency (days):", self.backup_frequency_spinbox)

        self.backup_location_edit = QLineEdit(self.settings.get("backup_location", ""))
        backup_location_button = QPushButton("Browse")
        backup_location_button.clicked.connect(self.select_backup_location)
        backup_location_layout = QHBoxLayout()
        backup_location_layout.addWidget(self.backup_location_edit)
        backup_location_layout.addWidget(backup_location_button)
        backup_layout.addRow("Backup Location:", backup_location_layout)

        backup_widget.setLayout(backup_layout)
        tabs.addTab(backup_widget, "Backup")

        update_widget = QWidget()
        update_layout = QFormLayout()

        self.check_for_updates_checkbox = QCheckBox("Check for Updates on Startup")
        self.check_for_updates_checkbox.setChecked(self.settings.get("check_for_updates", True))
        update_layout.addRow(self.check_for_updates_checkbox)

        self.update_schedule_combo = QComboBox()
        self.update_schedule_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.update_schedule_combo.setCurrentText(self.settings.get("update_schedule", "Weekly"))
        update_layout.addRow("Update Schedule:", self.update_schedule_combo)

        check_updates_button = QPushButton("Check for Updates")
        check_updates_button.clicked.connect(self.check_for_updates)
        update_layout.addRow(check_updates_button)

        update_widget.setLayout(update_layout)
        tabs.addTab(update_widget, "Update")

        advanced_widget = QWidget()
        advanced_layout = QFormLayout()

        self.enable_error_logging_checkbox = QCheckBox("Enable Error Logging")
        self.enable_error_logging_checkbox.setChecked(self.settings.get("enable_error_logging", True))
        advanced_layout.addRow(self.enable_error_logging_checkbox)

        self.debug_mode_checkbox = QCheckBox("Enable Debug Mode")
        self.debug_mode_checkbox.setChecked(self.settings.get("debug_mode", False))
        advanced_layout.addRow(self.debug_mode_checkbox)

        self.cache_timeout_spinbox = QSpinBox()
        self.cache_timeout_spinbox.setRange(1, 300)
        self.cache_timeout_spinbox.setValue(self.settings.get("cache_timeout", 60))
        advanced_layout.addRow("Cache Timeout (seconds):", self.cache_timeout_spinbox)

        advanced_widget.setLayout(advanced_layout)
        tabs.addTab(advanced_widget, "Advanced")

        main_layout.addWidget(tabs)

        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_settings(dialog))
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)
        dialog.setLayout(main_layout)

        dialog.exec_()

    def toggle_custom_json_path(self, text):
        if text == "Custom":
            self.custom_json_path_edit.setEnabled(True)
            self.custom_json_path_button.setEnabled(True)
        else:
            self.custom_json_path_edit.setEnabled(False)
            self.custom_json_path_button.setEnabled(False)

    def save_settings(self, dialog):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["highlight_color"] = self.highlight_color_edit.text()
        self.settings["font_color"] = self.font_color_edit.text()
        self.settings["background_color"] = self.background_color_edit.text()
        self.settings["alternate_background_color"] = self.alternate_background_color_edit.text()
        self.settings["border_color"] = self.border_color_edit.text()
        self.settings["button_hover_color"] = self.button_hover_color_edit.text()
        self.settings["button_press_color"] = self.button_press_color_edit.text()
        self.settings["toolbar_bg_start"] = self.toolbar_bg_start_edit.text()
        self.settings["toolbar_bg_end"] = self.toolbar_bg_end_edit.text()
        self.settings["dialog_bg_color"] = self.dialog_bg_color_edit.text()
        self.settings["label_color"] = self.label_color_edit.text()

        self.settings["font_size"] = self.font_size_spinbox.value()
        self.settings["row_height"] = self.row_height_spinbox.value()
        self.settings["show_grid"] = self.show_grid_checkbox.isChecked()
        self.settings["alternate_row_colors"] = self.alternate_row_colors_checkbox.isChecked()

        self.settings["shortcut_new_file"] = self.shortcut_new_file_edit.text()
        self.settings["shortcut_add"] = self.shortcut_add_edit.text()
        self.settings["shortcut_edit"] = self.shortcut_edit_edit.text()
        self.settings["shortcut_open"] = self.shortcut_open_edit.text()
        self.settings["shortcut_save"] = self.shortcut_save_edit.text()
        self.settings["shortcut_save_as"] = self.shortcut_save_as_edit.text()
        self.settings["shortcut_undo"] = self.shortcut_undo_edit.text()
        self.settings["shortcut_redo"] = self.shortcut_redo_edit.text()
        self.settings["shortcut_delete"] = self.shortcut_delete_edit.text()

        self.settings["default_csv_path"] = self.default_csv_path_edit.text()
        self.settings["default_json_path"] = self.default_json_path_edit.text()
        self.settings["startup_json"] = self.startup_json_combo.currentText()
        self.settings["custom_json_path"] = self.custom_json_path_edit.text()

        self.settings["auto_save_interval"] = self.auto_save_interval_spinbox.value()
        self.settings["enable_notifications"] = self.enable_notifications_checkbox.isChecked()
        self.settings["default_export_format"] = self.default_export_format_combo.currentText()
        self.settings["backup_frequency"] = self.backup_frequency_spinbox.value()
        self.settings["backup_location"] = self.backup_location_edit.text()

        self.settings["check_for_updates"] = self.check_for_updates_checkbox.isChecked()
        self.settings["update_schedule"] = self.update_schedule_combo.currentText()

        self.settings["enable_error_logging"] = self.enable_error_logging_checkbox.isChecked()
        self.settings["debug_mode"] = self.debug_mode_checkbox.isChecked()
        self.settings["cache_timeout"] = self.cache_timeout_spinbox.value()

        save_settings(self.settings)
        self.apply_theme()
        self.apply_table_settings()
        dialog.accept()

    def select_color(self, setting, line_edit, canvas):
        color = QColorDialog.getColor()
        if color.isValid():
            line_edit.setText(color.name())
            canvas.setStyleSheet(f"background-color: {color.name()};")
            self.settings[setting] = color.name()

    def restore_default_colors(self):
        self.highlight_color_edit.setText(DEFAULT_SETTINGS["highlight_color"])
        self.font_color_edit.setText(DEFAULT_SETTINGS["font_color"])
        self.background_color_edit.setText(DEFAULT_SETTINGS["background_color"])
        self.alternate_background_color_edit.setText(DEFAULT_SETTINGS["alternate_background_color"])
        self.border_color_edit.setText(DEFAULT_SETTINGS["border_color"])
        self.button_hover_color_edit.setText(DEFAULT_SETTINGS["button_hover_color"])
        self.button_press_color_edit.setText(DEFAULT_SETTINGS["button_press_color"])
        self.toolbar_bg_start_edit.setText(DEFAULT_SETTINGS["toolbar_bg_start"])
        self.toolbar_bg_end_edit.setText(DEFAULT_SETTINGS["toolbar_bg_end"])
        self.dialog_bg_color_edit.setText(DEFAULT_SETTINGS["dialog_bg_color"])
        self.label_color_edit.setText(DEFAULT_SETTINGS["label_color"])

        self.apply_theme()

    def apply_color_palette(self, palette_name):
        palettes = {
            "Default": DEFAULT_SETTINGS,
            "Cool Blues": {
                "highlight_color": "#3399ff",
                "font_color": "#e6f2ff",
                "background_color": "#00264d",
                "alternate_background_color": "#001a33",
                "border_color": "#3399ff",
                "button_hover_color": "#3399ff",
                "button_press_color": "#2673cc",
                "toolbar_bg_start": "#003366",
                "toolbar_bg_end": "#00264d",
                "dialog_bg_color": "#00264d",
                "label_color": "#e6f2ff"
            },
            "Warm Sunset": {
                "highlight_color": "#ff9966",
                "font_color": "#fff2e6",
                "background_color": "#4d2600",
                "alternate_background_color": "#331a00",
                "border_color": "#ff9966",
                "button_hover_color": "#ff9966",
                "button_press_color": "#cc8052",
                "toolbar_bg_start": "#663300",
                "toolbar_bg_end": "#4d2600",
                "dialog_bg_color": "#4d2600",
                "label_color": "#fff2e6"
            },
            "Forest Greens": {
                "highlight_color": "#66cc66",
                "font_color": "#e6ffe6",
                "background_color": "#003300",
                "alternate_background_color": "#002600",
                "border_color": "#66cc66",
                "button_hover_color": "#66cc66",
                "button_press_color": "#52a652",
                "toolbar_bg_start": "#004d00",
                "toolbar_bg_end": "#003300",
                "dialog_bg_color": "#003300",
                "label_color": "#e6ffe6"
            },
            "Desert Sands": {
                "highlight_color": "#cc9933",
                "font_color": "#fffbf2",
                "background_color": "#4d3b00",
                "alternate_background_color": "#332800",
                "border_color": "#cc9933",
                "button_hover_color": "#cc9933",
                "button_press_color": "#a67c29",
                "toolbar_bg_start": "#665000",
                "toolbar_bg_end": "#4d3b00",
                "dialog_bg_color": "#4d3b00",
                "label_color": "#fffbf2"
            }
        }
        selected_palette = palettes.get(palette_name, DEFAULT_SETTINGS)
        self.highlight_color_edit.setText(selected_palette["highlight_color"])
        self.font_color_edit.setText(selected_palette["font_color"])
        self.background_color_edit.setText(selected_palette["background_color"])
        self.alternate_background_color_edit.setText(selected_palette["alternate_background_color"])
        self.border_color_edit.setText(selected_palette["border_color"])
        self.button_hover_color_edit.setText(selected_palette["button_hover_color"])
        self.button_press_color_edit.setText(selected_palette["button_press_color"])
        self.toolbar_bg_start_edit.setText(selected_palette["toolbar_bg_start"])
        self.toolbar_bg_end_edit.setText(selected_palette["toolbar_bg_end"])
        self.dialog_bg_color_edit.setText(selected_palette["dialog_bg_color"])
        self.label_color_edit.setText(selected_palette["label_color"])

        self.apply_theme()

    def apply_theme(self):
        if self.settings["theme"] == "dark":
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            self.setStyleSheet("")

    def apply_table_settings(self):
        self.table.setAlternatingRowColors(self.settings["alternate_row_colors"])
        self.table.setShowGrid(self.settings["show_grid"])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {self.settings.get('highlight_color', '#3a7ae0')};
                font-size: {self.settings.get('font_size', 14)}pt;
                alternate-background-color: {self.settings.get('alternate_background_color', '#2e2e2e')};
                background-color: {self.settings.get('background_color', '#1e1e1e')};
                color: {self.settings.get('font_color', 'white')};
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {self.settings.get('highlight_color', '#3a7ae0')};
                padding: 10px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.settings.get('highlight_color', '#5a9ae0')};
                color: white;
            }}
        """)
        self.table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {self.settings.get('highlight_color', '#3a7ae0')};
                color: {self.settings.get('font_color', 'white')};
                font-weight: bold;
                font-size: {self.settings.get('font_size', 12)}pt;
                padding: 5px;
                border: 1px solid {self.settings.get('highlight_color', '#3a7ae0')};
            }}
        """)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(self.settings["shortcut_new_file"]), self, self.new_file)
        QShortcut(QKeySequence(self.settings["shortcut_add"]), self, self.add_item)
        QShortcut(QKeySequence(self.settings["shortcut_edit"]), self, self.edit_selected_item)
        QShortcut(QKeySequence(self.settings["shortcut_open"]), self, self.open_file)
        QShortcut(QKeySequence(self.settings["shortcut_save"]), self, self.save_file)
        QShortcut(QKeySequence(self.settings["shortcut_save_as"]), self, self.save_file_as)
        QShortcut(QKeySequence(self.settings["shortcut_undo"]), self, self.undo)
        QShortcut(QKeySequence(self.settings["shortcut_redo"]), self, self.redo)
        QShortcut(QKeySequence(self.settings["shortcut_delete"]), self, self.delete_selected_items)

    def undo(self):
        if self.undo_stack:
            action, item = self.undo_stack.pop()
            if action == "remove":
                self.data.append(item)
            elif action == "add":
                self.data = [i for i in self.data if i != item]
            self.redo_stack.append((action, item))
            self.populate_listbox(self.data)
            self.save_file()

    def redo(self):
        if self.redo_stack:
            action, item = self.redo_stack.pop()
            if action == "remove":
                self.data = [i for i in self.data if i != item]
            elif action == "add":
                self.data.append(item)
            self.undo_stack.append((action, item))
            self.populate_listbox(self.data)
            self.save_file()

    def show_help_dialog(self):
        help_window = HelpWindow(self)  # Pass 'self' as the parent
        help_window.show()

    def show_about_dialog(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def check_for_updates(self):
        self.status_bar.showMessage("Checking for updates...")
        self.update_thread = UpdateCheckThread()
        self.update_thread.update_available.connect(self.on_update_check_complete)
        self.update_thread.start()

    def on_update_check_complete(self, update_available, latest_version, exe_url):
        if update_available:
            reply = QMessageBox.question(
                self,
                'Update Available',
                f"A new version ({latest_version}) is available. Do you want to update?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                update_dialog = UpdateDialog(exe_url, self)
                update_dialog.exec_()
            else:
                self.status_bar.showMessage("Update postponed.")
        else:
            if latest_version:
                QMessageBox.information(self, "No Update", f"You are using the latest version ({latest_version}).")
            else:
                QMessageBox.warning(self, "Update Check Failed", "Failed to check for updates.")
    
        self.status_bar.showMessage("Ready")




    def select_default_csv_path(self):
        options = QFileDialog.Options()
        file_path = QFileDialog.getExistingDirectory(self, "Select Default CSV Path", options=options)
        if file_path:
            self.default_csv_path_edit.setText(file_path)

    def select_default_json_path(self):
        options = QFileDialog.Options()
        file_path = QFileDialog.getExistingDirectory(self, "Select Default JSON Path", options=options)
        if file_path:
            self.default_json_path_edit.setText(file_path)

    def select_custom_json_path(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Custom JSON File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            self.custom_json_path_edit.setText(file_path)

    def restore_starfield_json(self):
        backup_file = os.path.join(self.settings.get("backup_location", ""), "Starfield.json.bak")
        if os.path.exists(backup_file):
            shutil.copy(backup_file, "Starfield.json")
            self.status_bar.showMessage("Starfield.json restored from backup.")
        else:
            self.status_bar.showMessage("No backup found to restore.")

    def select_backup_location(self):
        options = QFileDialog.Options()
        file_path = QFileDialog.getExistingDirectory(self, "Select Backup Location", options=options)
        if file_path:
            self.backup_location_edit.setText(file_path)

    def add_item(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Item")
        layout = QFormLayout()
        item_code_edit = QLineEdit()
        item_name_edit = QLineEdit()
        console_command_edit = QLineEdit()
        layout.addRow("Item Code:", item_code_edit)
        layout.addRow("Item Name:", item_name_edit)
        layout.addRow("Console Command:", console_command_edit)
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.save_new_item(dialog, item_code_edit, item_name_edit, console_command_edit))
        layout.addWidget(add_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_new_item(self, dialog, item_code_edit, item_name_edit, console_command_edit):
        new_item = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text()
        }
        self.data.append(new_item)
        self.populate_listbox(self.data)
        self.save_file()
        dialog.accept()

    def edit_selected_item(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            item_code = self.table.item(selected_row, 0).text()
            item_name = self.table.item(selected_row, 1).text()
            console_command = self.table.cellWidget(selected_row, 2).layout().itemAt(0).widget().text()

            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Item")
            layout = QFormLayout()
            item_code_edit = QLineEdit(item_code)
            item_name_edit = QLineEdit(item_name)
            console_command_edit = QLineEdit(console_command)
            layout.addRow("Item Code:", item_code_edit)
            layout.addRow("Item Name:", item_name_edit)
            layout.addRow("Console Command:", console_command_edit)
            save_button = QPushButton("Save")
            save_button.clicked.connect(lambda: self.save_edit(dialog, selected_row, item_code_edit, item_name_edit, console_command_edit))
            layout.addWidget(save_button)
            dialog.setLayout(layout)
            dialog.exec_()

    def save_edit(self, dialog, row, item_code_edit, item_name_edit, console_command_edit):
        self.table.setItem(row, 0, QTableWidgetItem(item_code_edit.text()))
        self.table.setItem(row, 1, QTableWidgetItem(item_name_edit.text()))
        cell_widget = self.table.cellWidget(row, 2)
        cell_widget.layout().itemAt(0).widget().setText(console_command_edit.text())

        self.data[row] = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text()
        }

        with open(self.current_file, 'w') as jsonfile:
            json.dump(self.data, jsonfile)

        dialog.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)  # Ensure this is the first PyQt5 object created
    viewer = JSONViewerApp([])     # Now you can create widgets
    sys.exit(app.exec_())
