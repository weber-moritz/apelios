import logging
import cv2
import sys
import asyncio

from qasync import QEventLoop
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QSize, Qt, QMargins
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QSlider,
    QSizePolicy
)

from reciever import run_receiver

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("My App")
        
        self.video_label = QLabel()
        self.video_label.setScaledContents(False)  # Don't stretch!
        self.video_label.setAlignment(Qt.AlignCenter)  # Center the video
        
        # Allow the label to shrink below its content size
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        self.setCentralWidget(self.video_label)
                
        self.resize(800, 600)
        
        # Set a reasonable minimum window size (not content-dependent)
        self.setMinimumSize(320, 240)  # Reasonable minimum for usability
        
        # Store the original pixmap for rescaling
        self.original_pixmap = None
        
        
    def display_frame(self, frame_array):
        rgb_frame = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
        
        height, width, channels = rgb_frame.shape
        bytes_per_line = 3 * width
        
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.original_pixmap = QPixmap.fromImage(q_image)
        
        # Update the display
        self._update_video_display()
    
    def _update_video_display(self):
        """Scale and display the video frame."""
        if self.original_pixmap:
            # Scale to fit while maintaining aspect ratio
            scaled_pixmap = self.original_pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """Handle window resize - rescale video to fit new size."""
        super().resizeEvent(event)
        self._update_video_display()
        
        
        
    async def start_video(self):
        await run_receiver(
            host= "127.0.0.1",
            port=9999,
            display=False,
            frame_callback=self.display_frame
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # Use qasync event loop instead of QtAsyncio
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    
    # Run the async video receiver with qasync
    with loop:
        loop.run_until_complete(window.start_video())