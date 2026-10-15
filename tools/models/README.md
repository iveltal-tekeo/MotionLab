# Models shipped with MotionLab

Small, CPU-only model files the lab loads with what is already installed (OpenCV) - nothing to download or install.

| File | What for | Source | Licence | Size / SHA-256 |
|---|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | faces in thumbnail candidates and the thumbnail check (`motionlab\thumbnail.py`, `cv2.FaceDetectorYN`) | OpenCV model zoo, `models/face_detection_yunet` (YuNet, Shiqi Yu) | MIT - `LICENSE-yunet.txt` | 232,589 bytes, `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |

Added 2026-10-15 (0.4.3, the user's choice) after measuring on this lab's footage: a talking-head phone video 15 of 15
faces, a 4K room video 26 of 29 (missed: 2 side profiles, 1 small far face), no false faces above the 0.88 score
cut-off, 8-14 ms a frame at 640 px on the CPU. OpenCV 5 has no Haar cascades, so this is the light face detector.
The file was downloaded from the official zoo and checked against the copy used for the measurements (same SHA-256).
