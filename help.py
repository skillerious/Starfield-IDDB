import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QTabWidget, QTextEdit
from PyQt5.QtGui import QIcon
import qdarkstyle


class HelpWindow(QDialog):
    def __init__(self, parent=None):  # Accept parent as an optional argument
        super().__init__(parent)  # Pass the parent to the superclass constructor
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Help")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('images/help.png'))
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self.create_tab(self.get_overview_text()), "Overview")
        tabs.addTab(self.create_tab(self.get_features_text()), "Features")
        tabs.addTab(self.create_tab(self.get_usage_text()), "Usage")
        tabs.addTab(self.create_tab(self.get_shortcuts_text()), "Shortcuts")
        tabs.addTab(self.create_tab(self.get_settings_text()), "Settings")
        tabs.addTab(self.create_tab(self.get_favorites_text()), "Favorites")
        tabs.addTab(self.create_tab(self.get_advanced_features_text()), "Advanced Features")

        layout.addWidget(tabs)

    def create_tab(self, text):
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(text)
        return text_edit

    def get_overview_text(self):
        return """
        <h1 style="font-size:18px;">Overview</h1>
        <p style="font-size:14px;">Welcome to <b>Starfield IDDB</b>! This application helps you manage and view Starfield console commands.</p>
        
        <h2 style="font-size:16px;">Main Purpose</h2>
        <ul style="font-size:14px;">
            <li><b>Manage Console Commands</b>: Easily add, edit, and delete commands.</li>
            <li><b>Organize Your Data</b>: Keep your commands organized in a JSON file format.</li>
            <li><b>Search and Filter</b>: Quickly find the commands you need.</li>
        </ul>
        
        <p style="font-size:14px;">Enjoy using Starfield IDDB to enhance your gameplay experience!</p>
        """

    def get_features_text(self):
        return """
        <h1 style="font-size:18px;">Features</h1>
        
        <h2 style="font-size:16px;">Main Features</h2>
        <ul style="font-size:14px;">
            <li><b>New File</b>: Create a new JSON file.</li>
            <li><b>Add</b>: Add a new item to the current JSON file.</li>
            <li><b>Open</b>: Open an existing JSON file.</li>
            <li><b>Save</b>: Save the current JSON file.</li>
            <li><b>Save As</b>: Save the current JSON file with a new name.</li>
            <li><b>Print</b>: Print the current view.</li>
            <li><b>Export to CSV</b>: Export the current JSON data to a CSV file.</li>
            <li><b>Export to JSON</b>: Export the current JSON data to a new JSON file.</li>
            <li><b>Export to PDF</b>: Export the current view to a PDF file.</li>
            <li><b>Undo</b>: Undo the last action.</li>
            <li><b>Redo</b>: Redo the last undone action.</li>
            <li><b>Refresh</b>: Refresh the current view.</li>
            <li><b>Delete</b>: Delete the selected items from the current JSON file.</li>
            <li><b>Settings</b>: Open the settings dialog.</li>
            <li><b>Help</b>: Show this help dialog.</li>
            <li><b>About</b>: Show information about the application.</li>
        </ul>
        
        <h2 style="font-size:16px;">Additional Features</h2>
        <ul style="font-size:14px;">
            <li><b>Favorites</b>: Mark commands as favorites for quick access.</li>
            <li><b>History</b>: View your recent actions and commands.</li>
            <li><b>Advanced Search</b>: Use detailed criteria to find specific items.</li>
            <li><b>Theme Customization</b>: Change the appearance of the application.</li>
        </ul>
        """

    def get_usage_text(self):
        return """
        <h1 style="font-size:18px;">Usage</h1>
        
        <h2 style="font-size:16px;">Table Features</h2>
        <ul style="font-size:14px;">
            <li><b>Search Bar</b>: Use the search bar to filter items based on their ID, name, or console command.</li>
            <li><b>Advanced Search</b>: Use the advanced search button to specify more detailed search criteria.</li>
            <li><b>Context Menu</b>: Right-click on an item to add it to favorites, copy its console command, or edit it.</li>
            <li><b>Double Click</b>: Double-click on an item to view its details.</li>
            <li><b>Favorites</b>: Click the star icon to add/remove an item to/from favorites.</li>
        </ul>
        
        <h2 style="font-size:16px;">Tips</h2>
        <ul style="font-size:14px;">
            <li><b>Efficient Searching</b>: Use keywords and filters to quickly locate specific commands.</li>
            <li><b>Organizing Data</b>: Regularly save your files and back up important data.</li>
        </ul>
        """

    def get_shortcuts_text(self):
        return """
        <h1 style="font-size:18px;">Keyboard Shortcuts</h1>
        
        <h2 style="font-size:16px;">General Shortcuts</h2>
        <ul style="font-size:14px;">
            <li><b>Ctrl+N</b>: Create a new file.</li>
            <li><b>Ctrl+A</b>: Add a new item.</li>
            <li><b>Ctrl+E</b>: Edit the selected item.</li>
            <li><b>Ctrl+O</b>: Open an existing file.</li>
            <li><b>Ctrl+S</b>: Save the current file.</li>
            <li><b>Ctrl+Shift+S</b>: Save the current file as a new file.</li>
            <li><b>Ctrl+Z</b>: Undo the last action.</li>
            <li><b>Ctrl+Shift+Z</b>: Redo the last undone action.</li>
            <li><b>Ctrl+Y</b>: Redo the last undone action.</li>
            <li><b>Delete</b>: Delete the selected items.</li>
        </ul>
        
        <h2 style="font-size:16px;">Navigation Shortcuts</h2>
        <ul style="font-size:14px;">
            <li><b>Alt+Tab</b>: Switch between tabs.</li>
            <li><b>Ctrl+F</b>: Open the search bar.</li>
        </ul>
        """

    def get_settings_text(self):
        return """
        <h1 style="font-size:18px;">Settings</h1>
        
        <h2 style="font-size:16px;">Appearance</h2>
        <ul style="font-size:14px;">
            <li><b>Theme</b>: Customize the appearance of the application, including colors and themes.</li>
            <li><b>Font Size</b>: Adjust the font size for better readability.</li>
            <li><b>Row Height</b>: Set the height of rows in tables.</li>
            <li><b>Grid Display</b>: Toggle the display of grid lines.</li>
        </ul>
        
        <h2 style="font-size:16px;">Shortcuts</h2>
        <ul style="font-size:14px;">
            <li><b>Customize Shortcuts</b>: Set custom keyboard shortcuts for various actions.</li>
        </ul>
        
        <h2 style="font-size:16px;">Defaults</h2>
        <ul style="font-size:14px;">
            <li><b>Default Paths</b>: Set default paths for CSV and JSON files.</li>
            <li><b>Startup File</b>: Specify the JSON file to load at startup.</li>
        </ul>
        
        <h2 style="font-size:16px;">Backup & Auto Save</h2>
        <ul style="font-size:14px;">
            <li><b>Auto Save Interval</b>: Set the interval for auto-saving your work.</li>
            <li><b>Notifications</b>: Enable or disable notifications for certain actions.</li>
            <li><b>Default Export Format</b>: Set the default format for exporting data.</li>
            <li><b>Backup Frequency</b>: Configure how often backups are created.</li>
        </ul>
        
        <h2 style="font-size:16px;">Advanced Settings</h2>
        <ul style="font-size:14px;">
            <li><b>Performance</b>: Adjust settings to improve application performance.</li>
            <li><b>Logging</b>: Enable or disable logging for troubleshooting purposes.</li>
        </ul>
        """

    def get_favorites_text(self):
        return """
        <h1 style="font-size:18px;">Favorites</h1>
        
        <h2 style="font-size:16px;">Managing Favorites</h2>
        <ul style="font-size:14px;">
            <li><b>Add to Favorites</b>: Click the star icon next to an item or use the context menu.</li>
            <li><b>Remove from Favorites</b>: Click the star icon again or use the context menu.</li>
            <li><b>Favorites Management</b>: Use the "Favorites Management" option in the toolbar to view and manage all favorite items.</li>
        </ul>
        
        <h2 style="font-size:16px;">Favorites Features</h2>
        <ul style="font-size:14px;">
            <li><b>Notes/Tags</b>: Add notes or tags to your favorite items for better organization.</li>
            <li><b>Sorting</b>: Sort favorites by various criteria to find them quickly.</li>
        </ul>
        """

    def get_advanced_features_text(self):
        return """
        <h1 style="font-size:18px;">Advanced Features</h1>
        
        <h2 style="font-size:16px;">Download and Update</h2>
        <ul style="font-size:14px;">
            <li><b>Update Application</b>: The application can download updates. You will be notified when a new update is available.</li>
            <li><b>Download Progress</b>: View the progress of the download and estimated time remaining.</li>
        </ul>
        
        <h2 style="font-size:16px;">Audit Log</h2>
        <ul style="font-size:14px;">
            <li><b>Action Logging</b>: All actions (add, edit, delete) are logged with timestamps for audit purposes.</li>
        </ul>
        
        <h2 style="font-size:16px;">Advanced Search</h2>
        <ul style="font-size:14px;">
            <li><b>Detailed Criteria</b>: Use the advanced search dialog to specify detailed search criteria.</li>
            <li><b>Search Options</b>: Search within item code, item name, or console command.</li>
        </ul>

        <h2 style="font-size:16px;">Export to PDF</h2>
        <ul style="font-size:14px;">
            <li><b>PDF Export</b>: Export the current view of the application to a PDF file for sharing or printing.</li>
            <li><b>High Quality</b>: The export function ensures high-quality output suitable for professional use.</li>
        </ul>
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    help_window = HelpWindow()
    help_window.show()
    sys.exit(app.exec_())
