#!/bin/bash
# Download YOLOv4-tiny model files for person detection

echo "Downloading YOLOv4-tiny model files..."

# Create models directory
mkdir -p models
cd models

# Download config
wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg

# Download weights
wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-tiny.weights

# Download COCO names
wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/data/coco.names

echo "Done! Model files downloaded to ./models/"
echo "Update receiver-3.py to use method='yolo' and point to these files"
