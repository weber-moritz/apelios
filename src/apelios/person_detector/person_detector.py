"""
person detection for video stream.
Detects and tracks people in real-time video stream using OpenCV built-in detectors.
"""


import asyncio
import cv2
import numpy as np
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class PersonDetector:
    """Person detection using HOG or Haar Cascade (OpenCV built-in only)."""
    
    def __init__(self, method="hog", confidence_threshold=0.5):
        """
        Initialize person detector.
        
        Args:
            method: Detection method - "hog" or "haar"
            confidence_threshold: Minimum confidence for detections (used for HOG)
        """
        self.method = method
        self.confidence_threshold = confidence_threshold
        self.person_count = 0
        
        logger.info(f"Initializing person detector with method: {method}")
        
        if method == "hog":
            self._init_hog()
        elif method == "haar":
            self._init_haar()
        else:
            logger.warning(f"Unknown method {method}, defaulting to HOG")
            self.method = "hog"
            self._init_hog()
    
    def _init_hog(self):
        """Initialize HOG (Histogram of Oriented Gradients) person detector."""
        try:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            logger.info("HOG detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize HOG: {e}")
            raise
    
    def _init_haar(self):
        """Initialize Haar Cascade for body detection."""
        try:
            self.haar_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            )
            if self.haar_cascade.empty():
                logger.warning("Failed to load fullbody cascade, trying upperbody")
                self.haar_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_upperbody.xml'
                )
            logger.info("Haar Cascade detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Haar Cascade: {e}")
            raise
    
    def detect_hog(self, frame):
        """Detect people using HOG."""
        detections = []
        try:
            # Resize frame for faster processing
            scale = 0.5
            small_frame = cv2.resize(frame, None, fx=scale, fy=scale)
            
            # Detect people with error handling
            boxes, weights = self.hog.detectMultiScale(
                small_frame,
                winStride=(8, 8),
                padding=(4, 4),
                scale=1.05
            )
            
            # Handle case where no detections
            if len(boxes) == 0:
                return detections
            
            # Scale boxes back to original size
            for i in range(len(boxes)):
                x, y, w, h = boxes[i]
                weight = weights[i]
                
                # Scale coordinates
                x, y, w, h = int(x/scale), int(y/scale), int(w/scale), int(h/scale)
                
                # Extract confidence value safely
                conf = float(weight[0]) if isinstance(weight, (list, tuple, np.ndarray)) else float(weight)
                
                detections.append({
                    'bbox': (x, y, w, h),
                    'confidence': conf
                })
        except Exception as e:
            logger.debug(f"Detection error (non-critical): {e}")
        
        return detections
    
    def detect_haar(self, frame):
        """Detect people using Haar Cascade."""
        detections = []
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            boxes = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Handle case where no detections
            if len(boxes) == 0:
                return detections
            
            for (x, y, w, h) in boxes:
                detections.append({
                    'bbox': (x, y, w, h),
                    'confidence': 1.0
                })
        except Exception as e:
            logger.debug(f"Detection error (non-critical): {e}")
        
        return detections
    
    def detect(self, frame):
        """
        Detect people in frame.
        
        Args:
            frame: BGR image
            
        Returns:
            List of detections with bbox and confidence
        """
        try:
            if self.method == "hog":
                return self.detect_hog(frame)
            elif self.method == "haar":
                return self.detect_haar(frame)
            else:
                return []
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def draw_detections(self, frame, detections, in_place=False):
        """
        Draw bounding boxes on frame.
        
        Args:
            frame: BGR image
            detections: List of detections
            in_place: If True, draw directly on frame (faster, modifies original)
            
        Returns:
            Annotated frame
        """
        annotated = frame if in_place else frame.copy()
        
        try:
            for det in detections:
                x, y, w, h = det['bbox']
                confidence = det['confidence']
                
                # Ensure coordinates are valid integers
                x, y, w, h = int(x), int(y), int(w), int(h)
                
                # Clamp coordinates to frame bounds
                height, width = frame.shape[:2]
                x = max(0, min(x, width - 1))
                y = max(0, min(y, height - 1))
                w = max(1, min(w, width - x))
                h = max(1, min(h, height - y))
                
                # Draw rectangle
                color = (0, 255, 0)  # Green
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"Person {confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                # Make sure label doesn't go out of bounds
                label_y = max(label_size[1] + 10, y)
                cv2.rectangle(annotated, (x, label_y - label_size[1] - 10), (x + label_size[0], label_y), color, -1)
                cv2.putText(annotated, label, (x, label_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        except Exception as e:
            logger.debug(f"Error drawing detections: {e}")
        
        return annotated
