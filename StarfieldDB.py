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
    QProgressBar, QColorDialog, QGroupBox, QListWidget
)
from PyQt5.QtGui import QColor, QBrush, QIcon, QKeySequence, QFont, QPainter, QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import qdarkstyle
from plyer import notification
import requests

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

class FavoritesManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Favorites")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        self.data = []
        self.load_favorites()

        layout = QVBoxLayout(self)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Item ID', 'Item Name', 'Console Command', 'Notes/Tags'])
        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #3a7ae0;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 5px;
                border: 1px solid #3a7ae0;
            }
        """)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #3a7ae0;
                font-size: 14pt;
                alternate-background-color: #2e2e2e;
                background-color: #1e1e1e;
                color: white;
            }
            QTableWidget::item {
                border-bottom: 1px solid #3a7ae0;
                padding: 10px;
            }
            QTableWidget::item:selected {
                background-color: #5a9ae0;
                color: white;
            }
        """)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.populate_table()

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add", self)
        self.add_button.clicked.connect(self.add_favorite)
        button_layout.addWidget(self.add_button)

        self.save_button = QPushButton("Save Changes", self)
        self.save_button.clicked.connect(self.save_favorites)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def load_favorites(self):
        if os.path.exists("Favourites.json"):
            with open("Favourites.json", "r") as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    self.data = []

    def populate_table(self):
        self.table.setRowCount(0)
        for index, item in enumerate(self.data):
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(self.table.rowCount() - 1, 0, QTableWidgetItem(item.get("Item Code", "")))
            self.table.setItem(self.table.rowCount() - 1, 1, QTableWidgetItem(item.get("Item Name", "")))
            self.table.setItem(self.table.rowCount() - 1, 2, QTableWidgetItem(item.get("Console Command", "")))
            self.table.setItem(self.table.rowCount() - 1, 3, QTableWidgetItem(item.get("Notes/Tags", "")))

            background_color = QBrush(QColor('#2e2e2e')) if index % 2 == 0 else QBrush(QColor('#1e1e1e'))
            for col in range(self.table.columnCount()):
                cell = self.table.item(index, col)
                if cell:
                    cell.setBackground(background_color)

            # Increase row height
            self.table.setRowHeight(self.table.rowCount() - 1, 50)

    def add_favorite(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Favorite")
        layout = QFormLayout()
        item_code_edit = QLineEdit()
        item_name_edit = QLineEdit()
        console_command_edit = QLineEdit()
        notes_tags_edit = QLineEdit()
        layout.addRow("Item Code:", item_code_edit)
        layout.addRow("Item Name:", item_name_edit)
        layout.addRow("Console Command:", console_command_edit)
        layout.addRow("Notes/Tags:", notes_tags_edit)
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.save_new_favorite(dialog, item_code_edit, item_name_edit, console_command_edit, notes_tags_edit))
        layout.addWidget(add_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_new_favorite(self, dialog, item_code_edit, item_name_edit, console_command_edit, notes_tags_edit):
        new_item = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text(),
            "Notes/Tags": notes_tags_edit.text()
        }
        self.data.append(new_item)
        self.populate_table()
        self.save_favorites()
        dialog.accept()

    def save_favorites(self):
        for row in range(self.table.rowCount()):
            self.data[row]["Notes/Tags"] = self.table.item(row, 3).text()

        with open("Favourites.json", "w") as f:
            json.dump(self.data, f)
        self.accept()

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
        self.recent_files = []
        self.settings = {
            "theme": "dark",
            "default_csv_path": "",
            "default_json_path": "",
            "startup_json": "Favourites",
            "custom_json_path": "",
            "font_size": 12,
            "show_grid": True,
            "row_height": 50,
            "alternate_row_colors": True,
            "highlight_color": "#3a7ae0",
            "font_color": "white",
            "background_color": "#1e1e1e",
            "alternate_background_color": "#2e2e2e",
            "auto_save_interval": 10,
            "enable_notifications": True,
            "default_export_format": "CSV",
            "backup_frequency": 30
        }
        self.buttons = {}  # Store the buttons here
        self.load_settings()
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

        # Create toolbar
        toolbar = QToolBar(self)
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3a3a3a, stop:1 #1e1e1e);
                border-bottom: 1px solid #3a7ae0;
                spacing: 10px;
                padding: 5px;
            }
            QToolButton {
                color: white;
                font-size: 12pt;
                padding: 5px;
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                background: #3a7ae0;
                border-radius: 5px;
            }
            QToolButton:pressed {
                background: #2a69bf;
                border-radius: 5px;
            }
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

        favorites_action = QAction(QIcon('images/favourite.png'), 'Favorites Management', self)
        favorites_action.triggered.connect(self.manage_favorites)
        toolbar.addAction(favorites_action)

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
        undo_action.setShortcut('Ctrl+Z')
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

        # Create search bar
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

        # Create buttons for JSON files
        buttons_layout = QHBoxLayout()
        for display_name in self.file_map:
            button = QPushButton(display_name, self)
            button.setFixedHeight(40)  # Set the height of the buttons
            button.setStyleSheet("""
                QPushButton {
                    padding: 10px;
                    font-size: 12pt;
                    border: 2px solid #3a7ae0;
                    color: white;
                    background-color: transparent;
                }
                QPushButton:checked {
                    background-color: #3a7ae0;
                }
            """)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, f=display_name: self.load_json_with_indicator(f))
            self.buttons[display_name] = button
            buttons_layout.addWidget(button)
        
        main_layout.addLayout(buttons_layout)

        # Create a stacked layout for the table and background
        stacked_layout = QVBoxLayout()

        # Create table to display JSON data
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Item ID', 'Item Name', 'Console Command', 'Favourite'])
        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #3a7ae0;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 5px;
                border: 1px solid #3a7ae0;
            }
        """)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {self.settings.get('highlight_color', '#3a7ae0')};
                font-size: 14pt;
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

        # Create detailed item view
        self.detail_view = QLabel("Select an item to view details", self)
        self.detail_view.setStyleSheet("color: white; padding: 10px; font-size: 12pt;")
        main_layout.addWidget(self.detail_view)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)
        
        self.setCentralWidget(main_widget)
        self.apply_theme()
        self.setup_shortcuts()
        self.load_startup_json()

        self.showMaximized()  # Ensure the application opens maximized

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

            # Create a QWidget to hold the console command and the buttons
            cell_widget = QWidget()
            cell_layout = QHBoxLayout()
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(10)

            # Console command label
            console_command_label = QLabel(item.get("Console Command", ""))
            console_command_label.setStyleSheet("color: white; background: transparent;")
            cell_layout.addWidget(console_command_label, stretch=1)

            # Copy button
            copy_button = QPushButton('Copy')
            copy_button.setStyleSheet("background: transparent; color: white; font-size: 10pt; border: none;")
            copy_button.setFixedSize(50, 28)  # Adjusted size of the button
            copy_button.clicked.connect(lambda ch, cmd=item.get("Console Command", ""): self.copy_command(cmd))
            cell_layout.addWidget(copy_button, stretch=0)

            cell_widget.setLayout(cell_layout)
            cell_widget.setStyleSheet("background: transparent;")
            self.table.setCellWidget(self.table.rowCount() - 1, 2, cell_widget)

            # Add star icon in the favourite column
            fav_item = QTableWidgetItem()
            icon_path = 'images/starfull.png' if self.is_favourite(item) else 'images/star.png'
            fav_item.setIcon(QIcon(icon_path))
            fav_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(self.table.rowCount() - 1, 3, fav_item)

            # Adjust the row height to accommodate the buttons
            self.table.setRowHeight(self.table.rowCount() - 1, self.settings["row_height"])

            # Alternate row color using QBrush and QColor
            background_color = QBrush(QColor(self.settings.get('alternate_background_color', '#2e2e2e'))) if index % 2 == 0 else QBrush(QColor(self.settings.get('background_color', '#1e1e1e')))
            for col in range(3):  # Updated to iterate only through the first three columns
                cell = self.table.item(index, col)
                if cell:
                    cell.setBackground(background_color)

    def schedule_search(self):
        self.search_timer.start(300)  # Debounce time of 300ms

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

        # Additional search options
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
        if column == 3:  # Star icon column
            item_code = self.table.item(row, 0).text()
            item_name = self.table.item(row, 1).text()
            console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
            item = {
                "Item Code": item_code,
                "Item Name": item_name,
                "Console Command": console_command
            }
            if self.is_favourite(item):
                self.remove_from_favourites(item)
                icon_path = os.path.join(os.getcwd(), 'images', 'starfield.png')
                notification.notify(
                    title='Starfield IDDB',
                    message=f'Removed {item_name} from favourites.',
                    app_name='Starfield IDDB',
                    app_icon=icon_path
                )
            else:
                self.add_to_favourites(item)
                icon_path = os.path.join(os.getcwd(), 'images', 'starfield.png')
                notification.notify(
                    title='Starfield IDDB',
                    message=f'Added {item_name} to favourites.',
                    app_name='Starfield IDDB',
                    app_icon=icon_path
                )
            self.populate_listbox(self.data)
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

    def is_favourite(self, item):
        if not os.path.exists("Favourites.json"):
            return False
        with open("Favourites.json", "r") as f:
            try:
                favourites = json.load(f)
            except json.JSONDecodeError:
                favourites = []
        return item in favourites

    def add_to_favourites(self, item):
        self.undo_stack.append(("remove", item))
        self.redo_stack.clear()
        if not os.path.exists("Favourites.json"):
            with open("Favourites.json", "w") as f:
                json.dump([item], f)
        else:
            with open("Favourites.json", "r") as f:
                try:
                    favourites = json.load(f)
                except json.JSONDecodeError:
                    favourites = []
            favourites.append(item)
            with open("Favourites.json", "w") as f:
                json.dump(favourites, f)
        audit_log.log("Add to Favourites", item)

    def remove_from_favourites(self, item):
        self.undo_stack.append(("add", item))
        self.redo_stack.clear()
        if not os.path.exists("Favourites.json"):
            return
        with open("Favourites.json", "r") as f:
            try:
                favourites = json.load(f)
            except json.JSONDecodeError:
                favourites = []
        favourites = [fav for fav in favourites if fav != item]
        with open("Favourites.json", "w") as f:
            json.dump(favourites, f)
        audit_log.log("Remove from Favourites", item)

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
        if self.is_favourite(item):
            remove_fav_action = QAction("Remove from Favourites", self)
            remove_fav_action.triggered.connect(lambda: self.remove_from_favourites_from_menu(position))
            context_menu.addAction(remove_fav_action)
        else:
            add_fav_action = QAction("Add to Favourites", self)
            add_fav_action.triggered.connect(lambda: self.add_to_favourites_from_menu(position))
            context_menu.addAction(add_fav_action)
        
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.copy_command(item.get("Console Command", "")))
        context_menu.addAction(copy_action)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.edit_item_from_menu(position))
        context_menu.addAction(edit_action)

        context_menu.exec_(self.table.viewport().mapToGlobal(position))

    def add_to_favourites_from_menu(self, position):
        row = self.table.indexAt(position).row()
        item_code = self.table.item(row, 0).text()
        item_name = self.table.item(row, 1).text()
        console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
        item = {
            "Item Code": item_code,
            "Item Name": item_name,
            "Console Command": console_command
        }
        self.add_to_favourites(item)
        self.populate_listbox(self.data)

    def remove_from_favourites_from_menu(self, position):
        row = self.table.indexAt(position).row()
        item_code = self.table.item(row, 0).text()
        item_name = self.table.item(row, 1).text()
        console_command = self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
        item = {
            "Item Code": item_code,
            "Item Name": item_name,
            "Console Command": console_command
        }
        self.remove_from_favourites(item)
        self.populate_listbox(self.data)

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
        # Update the table widget
        self.table.setItem(row, 0, QTableWidgetItem(item_code_edit.text()))
        self.table.setItem(row, 1, QTableWidgetItem(item_name_edit.text()))
        cell_widget = self.table.cellWidget(row, 2)
        cell_widget.layout().itemAt(0).widget().setText(console_command_edit.text())

        # Update the data list
        self.data[row] = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text()
        }

        # Save the updated data list to the current JSON file
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
                        'Yes' if self.is_favourite({
                            "Item Code": self.table.item(row, 0).text(),
                            "Item Name": self.table.item(row, 1).text(),
                            "Console Command": self.table.cellWidget(row, 2).layout().itemAt(0).widget().text()
                        }) else 'No'
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
            painter.drawPixmap(10, 10, screen)
            painter.end()
            self.status_bar.showMessage(f"Data exported to {file_path}")

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON File", self.settings.get("default_json_path", ""), "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            self.load_json(file_path)
            self.add_to_recent_files(file_path)

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
            painter.drawPixmap(10, 10, screen)
            painter.end()
            self.status_bar.showMessage("Printed successfully")

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout()

        # View GroupBox
        view_group = QGroupBox("View")
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

        view_group.setLayout(view_layout)

        # Color GroupBox
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout()

        self.highlight_color_button = QPushButton("Select Highlight Color")
        self.highlight_color_button.clicked.connect(lambda: self.select_color("highlight_color"))
        color_layout.addRow("Highlight Color:", self.highlight_color_button)

        self.font_color_button = QPushButton("Select Font Color")
        self.font_color_button.clicked.connect(lambda: self.select_color("font_color"))
        color_layout.addRow("Font Color:", self.font_color_button)

        self.background_color_button = QPushButton("Select Background Color")
        self.background_color_button.clicked.connect(lambda: self.select_color("background_color"))
        color_layout.addRow("Background Color:", self.background_color_button)

        self.alternate_background_color_button = QPushButton("Select Alternate Background Color")
        self.alternate_background_color_button.clicked.connect(lambda: self.select_color("alternate_background_color"))
        color_layout.addRow("Alternate Background Color:", self.alternate_background_color_button)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.settings["theme"])
        color_layout.addRow("Theme:", self.theme_combo)

        color_group.setLayout(color_layout)

        layout.addWidget(view_group)
        layout.addWidget(color_group)

        # Default Paths and Startup JSON GroupBox
        default_paths_group = QGroupBox("Default Paths and Startup JSON")
        default_paths_layout = QFormLayout()

        self.default_csv_path_edit = QLineEdit(self.settings.get("default_csv_path", ""))
        default_csv_path_button = QPushButton("Browse")
        default_csv_path_button.clicked.connect(self.select_default_csv_path)
        default_paths_layout.addRow("Default CSV Path:", self.default_csv_path_edit)
        default_paths_layout.addWidget(default_csv_path_button)

        self.default_json_path_edit = QLineEdit(self.settings.get("default_json_path", ""))
        default_json_path_button = QPushButton("Browse")
        default_json_path_button.clicked.connect(self.select_default_json_path)
        default_paths_layout.addRow("Default JSON Path:", self.default_json_path_edit)
        default_paths_layout.addWidget(default_json_path_button)

        startup_json_layout = QHBoxLayout()
        self.startup_json_combo = QComboBox()
        self.startup_json_combo.addItems(list(self.file_map.keys()) + ["Custom"])
        self.startup_json_combo.setCurrentText(self.settings["startup_json"])
        startup_json_layout.addWidget(self.startup_json_combo)

        self.custom_json_path_edit = QLineEdit(self.settings.get("custom_json_path", ""))
        self.custom_json_path_button = QPushButton("Browse")
        self.custom_json_path_button.clicked.connect(self.select_custom_json_path)
        startup_json_layout.addWidget(self.custom_json_path_edit)
        startup_json_layout.addWidget(self.custom_json_path_button)

        self.startup_json_combo.currentTextChanged.connect(self.toggle_custom_json_path)
        self.toggle_custom_json_path(self.startup_json_combo.currentText())

        default_paths_layout.addRow("Startup JSON:", startup_json_layout)

        default_paths_group.setLayout(default_paths_layout)
        layout.addWidget(default_paths_group)

        # Additional Settings GroupBox
        additional_settings_group = QGroupBox("Additional Settings")
        additional_settings_layout = QFormLayout()

        self.auto_save_interval_spinbox = QSpinBox()
        self.auto_save_interval_spinbox.setRange(1, 60)
        self.auto_save_interval_spinbox.setValue(self.settings.get("auto_save_interval", 10))
        additional_settings_layout.addRow("Auto-Save Interval (minutes):", self.auto_save_interval_spinbox)

        self.enable_notifications_checkbox = QCheckBox("Enable Notifications")
        self.enable_notifications_checkbox.setChecked(self.settings.get("enable_notifications", True))
        additional_settings_layout.addRow(self.enable_notifications_checkbox)

        self.default_export_format_combo = QComboBox()
        self.default_export_format_combo.addItems(["CSV", "JSON", "PDF"])
        self.default_export_format_combo.setCurrentText(self.settings["default_export_format"])
        additional_settings_layout.addRow("Default Export Format:", self.default_export_format_combo)

        self.backup_frequency_spinbox = QSpinBox()
        self.backup_frequency_spinbox.setRange(1, 60)
        self.backup_frequency_spinbox.setValue(self.settings.get("backup_frequency", 30))
        additional_settings_layout.addRow("Backup Frequency (minutes):", self.backup_frequency_spinbox)

        additional_settings_group.setLayout(additional_settings_layout)
        layout.addWidget(additional_settings_group)

        restore_button = QPushButton("Restore Starfield JSON")
        restore_button.clicked.connect(self.restore_starfield_json)
        layout.addWidget(restore_button)

        check_update_button = QPushButton("Check for Updates")
        check_update_button.clicked.connect(self.check_for_updates)
        layout.addWidget(check_update_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_settings_from_dialog(dialog))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def select_color(self, setting):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings[setting] = color.name()
            self.save_settings()

    def check_for_updates(self):
        version_url = "https://raw.githubusercontent.com/skillerious/RobinDoak/main/Version.txt"  # URL to the Version.txt file
        try:
            response = requests.get(version_url)
            response.raise_for_status()
            latest_version = response.text.strip()
            current_version = "1.0"  # Replace with actual current version
            if latest_version > current_version:
                reply = QMessageBox.question(self, 'Update Available', f'A new version ({latest_version}) is available. Do you want to download it?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    download_url = f"https://github.com/skillerious/RobinDoak/blob/main/Test-Version{latest_version}.exe"  # URL to the updated executable
                    update_dialog = UpdateDialog(download_url, self)
                    update_dialog.exec_()
            else:
                QMessageBox.information(self, "No Update Available", "You are currently using the latest version of Starfield IDDB.")
        except Exception as e:
            QMessageBox.warning(self, "Update Check Failed", f"Failed to check for updates: {e}")

    def select_custom_json_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Custom JSON File", self.settings.get("custom_json_path", ""), "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.custom_json_path_edit.setText(file_path)

    def toggle_custom_json_path(self, text):
        if text == "Custom":
            self.custom_json_path_edit.setEnabled(True)
            self.custom_json_path_button.setEnabled(True)
        else:
            self.custom_json_path_edit.setEnabled(False)
            self.custom_json_path_button.setEnabled(False)

    def restore_starfield_json(self):
        backup_folder = os.path.join(os.getcwd(), 'json backup')
        project_folder = os.getcwd()
        for file_name in os.listdir(backup_folder):
            src_file = os.path.join(backup_folder, file_name)
            dst_file = os.path.join(project_folder, file_name)
            shutil.copyfile(src_file, dst_file)
        self.show_notification('Starfield JSON files have been restored from backup.')
        self.refresh()

    def select_default_csv_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Default CSV Path")
        if path:
            self.default_csv_path_edit.setText(path)

    def select_default_json_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Default JSON Path")
        if path:
            self.default_json_path_edit.setText(path)

    def save_settings_from_dialog(self, dialog):
        self.settings["font_size"] = self.font_size_spinbox.value()
        self.settings["row_height"] = self.row_height_spinbox.value()
        self.settings["show_grid"] = self.show_grid_checkbox.isChecked()
        self.settings["alternate_row_colors"] = self.alternate_row_colors_checkbox.isChecked()
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["default_csv_path"] = self.default_csv_path_edit.text()
        self.settings["default_json_path"] = self.default_json_path_edit.text()
        self.settings["startup_json"] = self.startup_json_combo.currentText()
        self.settings["custom_json_path"] = self.custom_json_path_edit.text()
        self.settings["auto_save_interval"] = self.auto_save_interval_spinbox.value()
        self.settings["enable_notifications"] = self.enable_notifications_checkbox.isChecked()
        self.settings["default_export_format"] = self.default_export_format_combo.currentText()
        self.settings["backup_frequency"] = self.backup_frequency_spinbox.value()
        self.save_settings()
        dialog.accept()

    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                self.settings = {**self.settings, **json.load(f)}

    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)
        self.apply_theme()
        self.apply_customizations()

    def apply_theme(self):
        if self.settings["theme"] == "dark":
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            self.setStyleSheet("")

    def apply_customizations(self):
        font = self.font()
        font.setPointSize(self.settings.get("font_size", 12))
        self.setFont(font)
        self.table.setAlternatingRowColors(self.settings.get("alternate_row_colors", True))
        self.table.setShowGrid(self.settings.get("show_grid", True))
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, self.settings.get("row_height", 50))
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {self.settings.get('highlight_color', '#3a7ae0')};
                font-size: 14pt;
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

    def show_about_dialog(self):
        about_text = """
        <h2>About Starfield IDDB</h2>
        <p>Starfield IDDB is a robust application for viewing and managing Starfield item databases.</p>
        <p>Developed by Robin Doak.</p>
        <p>Version 1.0</p>
        """
        QMessageBox.about(self, "About Starfield IDDB", about_text)

    def show_help_dialog(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        layout = QVBoxLayout()

        help_text = """
        <h2>Starfield IDDB Help</h2>
        <ul>
            <li><b>New File:</b> Create a new JSON file.</li>
            <li><b>Add:</b> Add a new item to the current JSON file.</li>
            <li><b>Open:</b> Open an existing JSON file.</li>
            <li><b>Save:</b> Save the current JSON file.</li>
            <li><b>Save As:</b> Save the current JSON file with a new name.</li>
            <li><b>Print:</b> Print the current view.</li>
            <li><b>Export to CSV:</b> Export the current JSON data to a CSV file.</li>
            <li><b>Export to JSON:</b> Export the current JSON data to a new JSON file.</li>
            <li><b>Undo:</b> Undo the last action.</li>
            <li><b>Redo:</b> Redo the last undone action.</li>
            <li><b>Refresh:</b> Refresh the current view.</li>
            <li><b>Delete:</b> Delete the selected items from the current JSON file.</li>
            <li><b>Settings:</b> Open the settings dialog.</li>
            <li><b>Help:</b> Show this help dialog.</li>
            <li><b>About:</b> Show information about the application.</li>
        </ul>
        <h3>Table Features</h3>
        <ul>
            <li><b>Search Bar:</b> Use the search bar to filter items based on their ID, name, or console command.</li>
            <li><b>Advanced Search:</b> Use the advanced search button to specify more detailed search criteria.</li>
            <li><b>Context Menu:</b> Right-click on an item to add it to favourites, copy its console command, or edit it.</li>
            <li><b>Double Click:</b> Double-click on an item to view its details.</li>
            <li><b>Favourites:</b> Click the star icon to add/remove an item to/from favourites.</li>
        </ul>
        <h3>Keyboard Shortcuts</h3>
        <ul>
            <li><b>Ctrl+F:</b> Focus on the search bar.</li>
            <li><b>Ctrl+S:</b> Save the current JSON file.</li>
            <li><b>Ctrl+E:</b> Export the current JSON data to a CSV file.</li>
            <li><b>Ctrl+Z:</b> Undo the last action.</li>
            <li><b>Ctrl+Y:</b> Redo the last undone action.</li>
        </ul>
        """

        help_label = QLabel(help_text)
        help_label.setStyleSheet("color: white; font-size: 12pt;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)

        help_dialog.setLayout(layout)
        help_dialog.exec_()

    def show_notification(self, message):
        if self.settings.get("enable_notifications", True):
            icon_path = os.path.join(os.getcwd(), 'images', 'starfield.png')
            notification.notify(
                title='Starfield IDDB',
                message=message,
                app_name='Starfield IDDB',
                app_icon=icon_path
            )

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(lambda: self.search_entry.setFocus())
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.export_to_json)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_to_csv)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo)

    def undo(self):
        if not self.undo_stack:
            return
        action, item = self.undo_stack.pop()
        if action == "add":
            self.redo_stack.append(("remove", item))
            self.add_to_favourites(item)
        elif action == "remove":
            self.redo_stack.append(("add", item))
            self.remove_from_favourites(item)
        self.populate_listbox(self.data)

    def redo(self):
        if not self.redo_stack:
            return
        action, item = self.redo_stack.pop()
        if action == "add":
            self.undo_stack.append(("remove", item))
            self.add_to_favourites(item)
        elif action == "remove":
            self.undo_stack.append(("add", item))
            self.remove_from_favourites(item)
        self.populate_listbox(self.data)

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
        audit_log.log("Add Item", new_item)

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
        else:
            self.show_notification("No item selected for editing.")

    def manage_favorites(self):
        fav_manager = FavoritesManager(self)
        fav_manager.showMaximized()
        fav_manager.exec_()

    def save_edit(self, dialog, row, item_code_edit, item_name_edit, console_command_edit):
        # Update the table widget
        self.table.setItem(row, 0, QTableWidgetItem(item_code_edit.text()))
        self.table.setItem(row, 1, QTableWidgetItem(item_name_edit.text()))
        cell_widget = self.table.cellWidget(row, 2)
        cell_widget.layout().itemAt(0).widget().setText(console_command_edit.text())

        # Update the data list
        self.data[row] = {
            "Item Code": item_code_edit.text(),
            "Item Name": item_name_edit.text(),
            "Console Command": console_command_edit.text()
        }

        # Save the updated data list to the current JSON file
        with open(self.current_file, 'w') as jsonfile:
            json.dump(self.data, jsonfile)

        dialog.accept()

if __name__ == '__main__':
    json_files = [
        "Favourites.json",
        "PopularItems.json",
        "weapons.json",
        "ammo.json",
        "spacesuits.json",
        "helmets.json",
        "Boostpacks.json",
        "aid.json",
        "food.json",
        "skills.json",
        "book.json",
        "traits.json",
        "materials.json",
        "clothing.json"
    ]
    
    app = QApplication(sys.argv)
    viewer = JSONViewerApp(json_files)
    viewer.show()
    sys.exit(app.exec_())
