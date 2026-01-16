import sys

from PySide6.QtCore import QSize, Qt, QMargins
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QSlider
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("My App")
        
        self.label = QLabel()
        self.input = QLineEdit()
        self.list = QLabel()
        
        self.slider = QSlider()
        self.sliderText = QLabel()
        
        
        self.input.textChanged.connect(self.label.setText)
        
        self.button = QPushButton("Add to list")
        self.button.clicked.connect(self.add_to_list)
        
        self.slider.valueChanged.connect(lambda value: self.sliderText.setText(str(value)))
        
        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.label)
        layout.addWidget(self.list)
        layout.addWidget(self.button)
        layout.addWidget(self.slider)
        layout.addWidget(self.sliderText)
        
        container = QWidget()
        container.setLayout(layout)
        
        self.setCentralWidget(container)
        
    def add_to_list(self):
        temp = self.list.text() + "\n" + self.input.text()
        self.list.setText(temp)
        


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()