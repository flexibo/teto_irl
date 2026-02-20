import cv2
import mediapipe as mp
import pyautogui
import time
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

opts = mp_vision.PoseLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="pose_landmarker_lite.task"),
    num_poses=1,
)
detector = mp_vision.PoseLandmarker.create_from_options(opts)

cap = cv2.VideoCapture(0)

PTS = [11, 12, 13, 14, 15, 16, 23, 24, 0]

HARD_DROP_THRESHOLD  = 0.07
SOFT_DROP_THRESHOLD  = 0.07
RISE_THRESHOLD       = 0.07
CLOSE_THRESHOLD      = 0.05
HIGH_THRESHOLD       = 0.07
HORIZONTAL_THRESHOLD = 0.05
PROCESS_EVERY        = 10

DEBUG = False

prev_y11          = None
prev_y12          = None
prev_y23          = None
prev_y24          = None
softdrop_prev_y23 = None
softdrop_prev_y24 = None
soft_dropping     = False
last_detected     = ""
frame_count       = 0

def close(a, b, t=CLOSE_THRESHOLD):
    return abs(a.x - b.x) < t and abs(a.y - b.y) < t

def higher(a, b, t=HIGH_THRESHOLD):
    return (b.y - a.y) > t

def right_of(a, b, t=HORIZONTAL_THRESHOLD):
    return (a.x - b.x) > t

def left_of(a, b, t=HORIZONTAL_THRESHOLD):
    return (b.x - a.x) > t

while True:
    ok, frame = cap.read()
    frame = cv2.flip(frame, 1)
    if not ok:
        break

    frame_count += 1

    if frame_count % PROCESS_EVERY == 0:
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                          data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = detector.detect(mp_img)

        if results.pose_landmarks:
            h, w = frame.shape[:2]
            lms = results.pose_landmarks[0]

            for p in PTS:
                lm = lms[p]
                x, y = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

            p11, p12 = lms[11], lms[12]
            p13, p14 = lms[13], lms[14]
            p15, p16 = lms[15], lms[16]
            p23, p24 = lms[23], lms[24]
            p0       = lms[0]

            shoulders_dropped = False
            hips_dropped      = False
            hips_raised       = False

            if prev_y11 is not None and prev_y12 is not None:
                shoulders_dropped = (
                    (p11.y - prev_y11) > HARD_DROP_THRESHOLD and
                    (p12.y - prev_y12) > HARD_DROP_THRESHOLD
                )

            if prev_y23 is not None and prev_y24 is not None:
                hips_dropped = (
                    (p23.y - prev_y23) > SOFT_DROP_THRESHOLD and
                    (p24.y - prev_y24) > SOFT_DROP_THRESHOLD
                )

            if soft_dropping and softdrop_prev_y23 is not None:
                hips_raised = (
                    (softdrop_prev_y23 - p23.y) > RISE_THRESHOLD and
                    (softdrop_prev_y24 - p24.y) > RISE_THRESHOLD
                )

            arms_raised = higher(p16, p14) and higher(p15, p13)

            if not soft_dropping and arms_raised and hips_dropped:
                soft_dropping     = True
                softdrop_prev_y23 = p23.y
                softdrop_prev_y24 = p24.y
                pyautogui.keyDown("down")
                print("SOFT DROP start")

            if soft_dropping and hips_raised:
                soft_dropping     = False
                softdrop_prev_y23 = None
                softdrop_prev_y24 = None
                pyautogui.keyUp("down")
                print("SOFT DROP end")

            detected = None
            keypress = None

            if not soft_dropping and shoulders_dropped and not arms_raised:
                detected = "HARD DROP"
                keypress = "space"
            elif right_of(p14, p12) and close(p23, p24):
                detected = "CW SPIN"
                keypress = "x"
            elif left_of(p13, p11) and close(p23, p24):
                detected = "CCW SPIN"
                keypress = "z"
            elif higher(p13, p11) and higher(p12, p14):
                detected = "MOVE LEFT"
                keypress = "left"
            elif higher(p14, p12) and higher(p11, p13):
                detected = "MOVE RIGHT"
                keypress = "right"
            elif not soft_dropping and close(p15, p16) and p15.y < p0.y and p16.y < p0.y:
                detected = "HOLD"
                keypress = "c"

            if detected:
                last_detected = detected
                print(detected)
                pyautogui.press(keypress)

            prev_y11 = p11.y
            prev_y12 = p12.y
            prev_y23 = p23.y
            prev_y24 = p24.y

            if DEBUG:
                rise_delta = f"{softdrop_prev_y23 - p23.y:.3f}" if softdrop_prev_y23 else "n/a"

                debug_lines = [
                    (f"Status:           {'SOFT DROPPING' if soft_dropping else 'idle'}",      (0, 255, 255)),
                    (f"Arms raised:      {arms_raised}",                                        (0, 255, 0)),
                    (f"Shoulders dropped:{shoulders_dropped}",                                  (0, 255, 0)),
                    (f"Hips dropped:     {hips_dropped}",                                       (0, 255, 0)),
                    (f"Hips raised:      {hips_raised}",                                        (0, 255, 0)),
                    (f"Soft drop detect: {arms_raised and hips_dropped}",                       (0, 180, 255)),
                    (f"Rise delta:       {rise_delta}",                                         (0, 255, 0)),
                    (f"CW SPIN:          {right_of(p14, p12) and close(p23, p24)}",             (200, 200, 0)),
                    (f"CCW SPIN:         {left_of(p13, p11) and close(p23, p24)}",              (200, 200, 0)),
                    (f"MOVE LEFT:        {higher(p13, p11) and higher(p12, p14)}",              (200, 200, 0)),
                    (f"MOVE RIGHT:       {higher(p14, p12) and higher(p11, p13)}",              (200, 200, 0)),
                    (f"HOLD:             {close(p15, p16) and p15.y < p0.y and p16.y < p0.y}", (200, 200, 0)),
                    (f"Last detected:    {last_detected}",                                      (0, 100, 255)),
                ]

                for i, (text, color) in enumerate(debug_lines):
                    cv2.putText(frame, text, (10, 25 + i * 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Pose", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        if soft_dropping:
            pyautogui.keyUp("down")
        break

cap.release()
cv2.destroyAllWindows()
