import time
import cv2

try:
    from mediapipe.python.solutions import hands as mp_hands
    from mediapipe.python.solutions import drawing_utils as mp_draw
except Exception as e:
    print("MediaPipe import error:", e)
    mp_hands = None
    mp_draw = None


def count_fingers(hand_landmarks):
    """
    Counts how many fingers are raised.
    Returns a number from 0 to 5.
    """

    landmarks = hand_landmarks.landmark

    fingers = 0

    # Thumb
    # This is a simple thumb check using horizontal distance.
    if abs(landmarks[4].x - landmarks[2].x) > 0.08:
        fingers += 1

    # Index finger
    if landmarks[8].y < landmarks[6].y:
        fingers += 1

    # Middle finger
    if landmarks[12].y < landmarks[10].y:
        fingers += 1

    # Ring finger
    if landmarks[16].y < landmarks[14].y:
        fingers += 1

    # Pinky finger
    if landmarks[20].y < landmarks[18].y:
        fingers += 1

    return fingers



def capture_gesture_sequence(sequence_length: int = 3, hold_seconds: float = 1.0):
    """
    Opens the webcam and captures a gesture sequence.

    Example:
    5 -> 0 -> 2

    0 = fist
    1 = one finger
    2 = two fingers
    3 = three fingers
    4 = four fingers
    5 = open palm
    """

    if mp_hands is None or mp_draw is None:
        print("MediaPipe is not loaded correctly.")
        return None

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera could not be opened.")
        return None

    sequence = []
    current_gesture = None
    gesture_start_time = 0
    locked_gesture = None

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as hands:

        while True:
            success, frame = cap.read()

            if not success:
                print("Failed to read from camera.")
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb_frame)

            detected_gesture = None

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]

                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                detected_gesture = count_fingers(hand_landmarks)

                cv2.putText(
                    frame,
                    f"Detected gesture: {detected_gesture}",
                    (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2
                )

                # Prevent the same held gesture from being recorded again immediately
                if detected_gesture == locked_gesture:
                    cv2.putText(
                        frame,
                        "Change gesture or remove hand for next input",
                        (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

                else:
                    if detected_gesture != current_gesture:
                        current_gesture = detected_gesture
                        gesture_start_time = time.time()

                    else:
                        held_time = time.time() - gesture_start_time

                        if held_time >= hold_seconds:
                            sequence.append(detected_gesture)
                            locked_gesture = detected_gesture
                            current_gesture = None

                            print("Captured gesture:", detected_gesture)

                            time.sleep(0.5)

            else:
                current_gesture = None
                locked_gesture = None

            cv2.putText(
                frame,
                f"Sequence: {sequence}",
                (20, 420),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Hold each gesture for 1 second. Press q to cancel.",
                (20, 455),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.imshow("Gesture Login", frame)

            if len(sequence) == sequence_length:
                break

            if cv2.waitKey(1) & 0xFF == ord("q"):
                sequence = None
                break

    cap.release()
    cv2.destroyAllWindows()

    return sequence
def sequence_to_string(sequence):
    return "-".join(str(x) for x in sequence)