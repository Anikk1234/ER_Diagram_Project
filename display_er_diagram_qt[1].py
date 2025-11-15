import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

def display_er_diagram_qt():
    app = QApplication(sys.argv)

    script_dir = os.path.dirname(__file__)
    image_path = os.path.join(script_dir, 'data', 'decomposed', 'er_diagram.png')

    window = QWidget()
    window.setWindowTitle("ER Diagram")

    layout = QVBoxLayout()
    label = QLabel()
    label.setScaledContents(True) # Scale the pixmap to fit the label

    if not os.path.exists(image_path):
        label.setText(f"Error: Image not found at {image_path}")
        label.setAlignment(Qt.AlignCenter)
    else:
        try:
            pixmap = QPixmap()
            if not pixmap.load(image_path): # Explicitly load the image
                label.setText(f"Error: Could not load image from {image_path}")
                label.setAlignment(Qt.AlignCenter)
            else:
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignCenter)
                label.repaint() # Force redraw
        except Exception as e:
            label.setText(f"Error loading image: {e}")
            label.setAlignment(Qt.AlignCenter)

    scroll_area = QScrollArea()
    scroll_area.setWidget(label)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)
    
    window.setLayout(layout)
    window.showMaximized()

    sys.exit(app.exec_())

if __name__ == "__main__":
    display_er_diagram_qt()
