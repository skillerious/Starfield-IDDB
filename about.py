# about.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import qdarkstyle

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Starfield IDDB")
        self.setFixedSize(400, 400)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        layout = QVBoxLayout()

        # Add an image
        image_label = QLabel()
        pixmap = QPixmap('images/starfield.png')  # Path to your image
        scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # Application Name
        title_label = QLabel("<h2>Starfield IDDB</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QLabel("<p><b>Version:</b> 1.0</p>")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Developer Information
        developer_label = QLabel("<p><b>Developer:</b> Robin Doak</p>")
        developer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(developer_label)

        # Brief Description
        description_label = QLabel(
            "<p style='text-align:center;'>Starfield IDDB is an application designed to help you manage and view Starfield console commands. "
            "You can organize, search, and customize your commands effortlessly.</p>"
        )
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # GitHub Link
        github_label = QLabel("<p style='text-align:center;'>Check out my other projects on <a href='https://github.com/skillerious'>GitHub</a>.</p>")
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)

        # Close Button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(100)
        close_button.setStyleSheet("margin-top: 20px;")
        close_button.setDefault(True)

        # Center the close button
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)

        layout.addLayout(button_layout)

        self.setLayout(layout)
