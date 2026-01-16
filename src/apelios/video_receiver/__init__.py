"""
Video receiver module for Apelios.

WebRTC video stream receiver with optional real-time person detection using OpenCV built-in detectors.
"""

from .receiver import VideoReceiver, run_receiver

__all__ = ['VideoReceiver', 'run_receiver']
__version__ = '0.1.0'
