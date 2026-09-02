print("SCRIPT STARTED")

import cv2
import mediapipe as mp
import pyautogui
import time
import math

print("IMPORTS OK")
print("MediaPipe:", mp.__version__)
print("Has solutions:", hasattr(mp, "solutions"))


def distance(a, b):
    return math.hypot(
        a.x - b.x,
        a.y - b.y
    )

def elapsed(start_time):
    return time.time() - start_time

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))

def is_fist(landmarks):
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    curled = 0
    for tip, pip in zip(tips, pips):
        if landmarks[tip].y > landmarks[pip].y:
            curled += 1
    return curled == 4

def is_thumb_touch(landmarks):
    thumb = landmarks[4]
    palm = landmarks[5]
    return distance(thumb, palm) < 0.09

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)


screen_w, screen_h = pyautogui.size()

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

FRAME_LEFT = 0.35
FRAME_RIGHT = 0.80
FRAME_TOP = 0.35
FRAME_BOTTOM = 0.90

FRAME_MARGIN_X = 0.25
FRAME_MARGIN_Y = 0.25
DEADZONE = 0.015
MIN_SMOOTHING = 0.45
MAX_SMOOTHING = 0.90

smooth_x = None
smooth_y = None
cursor_mode = False
was_fist = False
clench_times = []
was_thumb_touch = False
touch_start = None
dragging = False
DRAG_THRESHOLD = 0.3

print("OPENING CAMERA")

cap = cv2.VideoCapture(0)
print("Camera opened:", cap.isOpened())

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame_h, frame_w, _ = frame.shape

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = hands.process(rgb)

    margin_left = int(frame_w * FRAME_LEFT)
    margin_right = int(frame_w * FRAME_RIGHT)

    margin_top = int(frame_h * FRAME_TOP)
    margin_bottom = int(frame_h * FRAME_BOTTOM)

    cv2.rectangle(
        frame,
        (margin_left, margin_top),
        (margin_right, margin_bottom),
        (255, 255, 255),
        2
    )

    if results.multi_hand_landmarks:
        hand_landmarks = (results.multi_hand_landmarks[0])
        lm = hand_landmarks.landmark

        mp_draw.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS
        )

        fist_now = is_fist(lm)

        if fist_now and not was_fist:
            now = time.time()
            clench_times.append(now)
            clench_times = [t for t in clench_times if now - t < 1.2]

            if len(clench_times) >= 2:
                cursor_mode = not cursor_mode
                clench_times = []

                smooth_x = None
                smooth_y = None

                if not cursor_mode and dragging:
                    pyautogui.mouseUp()
                    dragging = False

                print(f"Режим курсора: "f"{'ВКЛ' if cursor_mode else 'ВЫКЛ'}")

        was_fist = fist_now

        if cursor_mode and not fist_now:
            thumb_touch = is_thumb_touch(lm)

            if thumb_touch and not was_thumb_touch:
                touch_start = time.time()
                print("TOUCH START")

            if thumb_touch:
                if touch_start is not None:
                    current_elapsed = elapsed(touch_start)
                    if (current_elapsed > DRAG_THRESHOLD and not dragging):
                        dragging = True
                        pyautogui.mouseDown()
                        print("DRAG START")


            if not thumb_touch or dragging:
                index_tip = lm[8]

                x = (index_tip.x - FRAME_LEFT) / (FRAME_RIGHT - FRAME_LEFT)
                y = (index_tip.y - FRAME_TOP) / (FRAME_BOTTOM - FRAME_TOP)

                x = clamp(x,0.0,1.0)
                y = clamp(y,0.0,1.0)

                target_x = x * screen_w
                target_y = y * screen_h

                if smooth_x is None:
                    smooth_x = target_x
                    smooth_y = target_y


                else:
                    movement = math.hypot(target_x - smooth_x, target_y - smooth_y)
                    if movement < 30:
                        smoothing = MAX_SMOOTHING
                    else:
                        smoothing = MIN_SMOOTHING

                    smooth_x += (target_x - smooth_x) * smoothing
                    smooth_y += (target_y - smooth_y) * smoothing
                pyautogui.moveTo(int(smooth_x), int(smooth_y))

            if not thumb_touch and was_thumb_touch:
                if dragging:
                    pyautogui.mouseUp()
                    dragging = False
                    print("DRAG END")

                else:
                    pyautogui.click()
                    print("КЛИК")
                touch_start = None
            was_thumb_touch = thumb_touch


        else:
            was_thumb_touch = False
            touch_start = None

            if dragging:
                pyautogui.mouseUp()
                dragging = False

    else:
        was_fist = False
        was_thumb_touch = False
        touch_start = None

        if dragging:
            pyautogui.mouseUp()
            dragging = False
            print("DRAG END - HAND LOST")

    status = (
        "CURSOR ON"
        if cursor_mode
        else "CURSOR OFF"
    )

    if dragging:
        status += " | DRAGGING"


    cv2.putText(
        frame,
        status,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Hand Control", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


if dragging:
    pyautogui.mouseUp()

cap.release()
cv2.destroyAllWindows()
