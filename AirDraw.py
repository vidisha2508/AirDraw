import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import winsound

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

draw_layer = None
effect_layer = None
ui_layer = None

prev_x, prev_y = 0, 0
brush_size = 5

points = deque(maxlen=8)

colors = {
    "RED": (0, 0, 255),
    "GREEN": (0, 255, 0),
    "BLUE": (255, 0, 0)
}

draw_color = colors["GREEN"]

glow_enabled = True
rainbow_mode = False

status_text = "AIR CANVAS READY"
status_timer = 0

flash_timer = 0
button_cooldown = 0

rainbow_colors = [
    (0, 0, 255),
    (0, 255, 255),
    (0, 255, 0),
    (255, 255, 0),
    (255, 0, 0),
    (255, 0, 255)
]

rainbow_index = 0

buttons = [
    ("RED", (10, 10, 110, 60)),
    ("GREEN", (120, 10, 220, 60)),
    ("BLUE", (230, 10, 330, 60)),
    ("THIN", (360, 10, 470, 60)),
    ("THICK", (480, 10, 600, 60)),
    ("GLOW", (620, 10, 740, 60)),
    ("RAINBOW", (760, 10, 930, 60))
]

def play_sound(freq=1000, duration=120):
    winsound.Beep(freq, duration)

def set_status(text):

    global status_text
    global status_timer

    status_text = text
    status_timer = 40

def fingers_up(hand_landmarks):

    tips = [4, 8, 12, 16, 20]
    pip = [3, 6, 10, 14, 18]

    fingers = []

    if hand_landmarks.landmark[tips[0]].x < hand_landmarks.landmark[pip[0]].x:
        fingers.append(1)
    else:
        fingers.append(0)

    for i in range(1, 5):

        if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pip[i]].y:
            fingers.append(1)
        else:
            fingers.append(0)

    return fingers

while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    if button_cooldown > 0:
        button_cooldown -= 1

    if draw_layer is None:

        draw_layer = np.zeros_like(frame)
        effect_layer = np.zeros_like(frame)

    ui_layer = np.zeros_like(frame)

    for name, (x1, y1, x2, y2) in buttons:

        color = (60, 60, 60)

        if name == "RED":
            color = colors["RED"]

        elif name == "GREEN":
            color = colors["GREEN"]

        elif name == "BLUE":
            color = colors["BLUE"]

        elif name == "THIN" or name == "THICK":
            color = (0, 0, 0)

        elif name == "GLOW":
            color = (0, 255, 255)

        elif name == "RAINBOW":
            color = (255, 0, 255)

        cv2.rectangle(
            ui_layer,
            (x1, y1),
            (x2, y2),
            color,
            -1
        )

        cv2.rectangle(
            ui_layer,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2
        )

        cv2.putText(
            ui_layer,
            name,
            (x1 + 10, y1 + 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb)

    if results.multi_hand_landmarks:

        for hand_landmarks in results.multi_hand_landmarks:

            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            fingers = fingers_up(hand_landmarks)

            thumb, index, middle, ring, pinky = fingers

            x = int(hand_landmarks.landmark[8].x * w)
            y = int(hand_landmarks.landmark[8].y * h)

            if index == 1 and middle == 1:

                prev_x, prev_y = 0, 0

                for name, (x1, y1, x2, y2) in buttons:

                    if (
                        x1 < x < x2 and
                        y1 < y < y2 and
                        button_cooldown == 0
                    ):

                        play_sound()

                        button_cooldown = 60

                        if name in colors:

                            draw_color = colors[name]

                            rainbow_mode = False

                            set_status(f"{name} SELECTED")

                        elif name == "THIN":

                            brush_size = 3

                            set_status("THIN BRUSH")

                        elif name == "THICK":

                            brush_size = 12

                            set_status("THICK BRUSH")

                        elif name == "GLOW":

                            glow_enabled = not glow_enabled

                            if glow_enabled:
                                set_status("GLOW ENABLED")
                            else:
                                set_status("GLOW DISABLED")

                        elif name == "RAINBOW":

                            rainbow_mode = not rainbow_mode

                            if rainbow_mode:
                                set_status("RAINBOW MODE")
                            else:
                                set_status("RAINBOW OFF")

            elif index == 1 and middle == 0:

                if rainbow_mode:

                    draw_color = rainbow_colors[
                        rainbow_index % len(rainbow_colors)
                    ]

                    rainbow_index += 1

                points.append((x, y))

                smooth_x = int(np.mean([p[0] for p in points]))
                smooth_y = int(np.mean([p[1] for p in points]))

                if prev_x == 0 and prev_y == 0:

                    prev_x, prev_y = smooth_x, smooth_y

                cv2.line(
                    draw_layer,
                    (prev_x, prev_y),
                    (smooth_x, smooth_y),
                    draw_color,
                    brush_size
                )

                cv2.circle(
                    effect_layer,
                    (smooth_x, smooth_y),
                    brush_size * 2,
                    draw_color,
                    -1
                )

                prev_x, prev_y = smooth_x, smooth_y

                cv2.circle(
                    frame,
                    (smooth_x, smooth_y),
                    brush_size + 5,
                    draw_color,
                    -1
                )

            elif sum(fingers) == 0:

                prev_x, prev_y = 0, 0

                points.clear()

                if button_cooldown == 0:

                    draw_layer = np.zeros_like(frame)

                    effect_layer = np.zeros_like(frame)

                    flash_timer = 10

                    play_sound(1500, 200)

                    set_status("CANVAS CLEARED")

                    button_cooldown = 60

    effect_layer = cv2.addWeighted(
        effect_layer,
        0.90,
        np.zeros_like(effect_layer),
        0.10,
        0
    )

    if glow_enabled:

        blur1 = cv2.GaussianBlur(draw_layer, (15, 15), 0)
        blur2 = cv2.GaussianBlur(draw_layer, (31, 31), 0)
        blur3 = cv2.GaussianBlur(draw_layer, (61, 61), 0)

        glow = cv2.addWeighted(draw_layer, 1, blur1, 0.5, 0)
        glow = cv2.addWeighted(glow, 1, blur2, 0.3, 0)
        glow = cv2.addWeighted(glow, 1, blur3, 0.2, 0)

    else:

        glow = draw_layer.copy()

    output = cv2.addWeighted(frame, 0.75, glow, 1, 0)

    output = cv2.addWeighted(output, 1, effect_layer, 0.5, 0)

    output = cv2.addWeighted(output, 1, ui_layer, 1, 0)

    if flash_timer > 0:

        white = np.full_like(output, 255)

        output = cv2.addWeighted(
            output,
            0.3,
            white,
            0.7,
            0
        )

        cv2.putText(
            output,
            "CANVAS CLEARED",
            (300, 350),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (0, 0, 255),
            5
        )

        flash_timer -= 1

    if status_timer > 0:

        cv2.rectangle(
            output,
            (0, h - 45),
            (w, h),
            (20, 20, 20),
            -1
        )

        cv2.putText(
            output,
            status_text,
            (20, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2
        )

        status_timer -= 1

    cv2.putText(
        output,
        "AIR CANVAS",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.imshow("Air Canvas", output)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
