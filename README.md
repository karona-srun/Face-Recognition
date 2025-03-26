# Eye Sleep Detection

An advanced application that monitors eye state to detect drowsiness and prevent accidents due to falling asleep.

## Features

- **Advanced Eye Recognition**: Uses multiple techniques for reliable eye detection
- **Drowsiness Detection**: Monitors eye state to detect when a person is falling asleep
- **Wake-up Alarm**: Plays an audible alert when drowsiness is detected
- **Real-time Visual Feedback**: Shows detection status and drowsiness level

- **Menu System**:
  - Press 's' to toggle sound alerts on/off
  - Press 'v' to toggle visual feedback on/off
  - Press 'd' to toggle debug mode (shows detection boxes and measurements)
  - Press 'h' to show/hide help overlay
  - Press 'q' to quit the application

## Requirements

- Python 3.6+
- OpenCV (`pip install opencv-python`)
- NumPy (`pip install numpy`)
- Playsound for audio alerts (`pip install playsound`)
- *Optional* but recommended: dlib for improved facial landmark detection (`pip install dlib`)

## Installation

1. Clone or download this repository
2. Install the required packages:

```bash
pip install opencv-python numpy playsound
```

3. For enhanced recognition (recommended), install dlib:

```bash
pip install dlib
```

4. Download the shape predictor file for dlib:
   - Download from: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   - Extract the file to the same directory as the application

## Usage

1. Place an `alert.mp3` sound file in the same directory (this will be played when drowsiness is detected)
2. Run the application:

```bash
python face.py
```

3. Position yourself in front of the camera
4. The application will:
   - Detect your face and eyes
   - Monitor your eye state
   - Alert you if you appear to be falling asleep
   
5. Press 'q' to quit the application

## How It Works

This application uses:
- Multiple Haar Cascade classifiers for basic face and eye detection
- dlib's facial landmark detection for precise eye location and state measurement
- CLAHE (Contrast Limited Adaptive Histogram Equalization) for improved image quality
- Eye Aspect Ratio (EAR) calculation to determine if eyes are open or closed
- Non-maximum suppression to handle overlapping detections
- Temporal filtering to reduce false positives

## Troubleshooting

- **No camera access**: Ensure your webcam is connected and not in use by another application
- **Poor detection**: Ensure adequate lighting and face the camera directly
- **Sound not working**: Make sure `alert.mp3` is in the same directory as the application
- **dlib not working**: Ensure the shape predictor file is downloaded and placed correctly 