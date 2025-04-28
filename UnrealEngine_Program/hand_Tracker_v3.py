import cv2
import numpy as np
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient

# ── OSC 설정 ──────────────────────────────────────────────
UNREAL_IP, UNREAL_PORT = "127.0.0.1", 8000
osc_client = SimpleUDPClient(UNREAL_IP, UNREAL_PORT)
print(f"[INFO] OSC client → {UNREAL_IP}:{UNREAL_PORT}")

# ── MediaPipe Hands ───────────────────────────────────────
mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands      = mp_hands.Hands(static_image_mode=False,
                            max_num_hands=1,
                            min_detection_confidence=0.5,
                            min_tracking_confidence=0.5)

SMOOTHING_ALPHA = 0.4
smooth_lms = None  # 첫 프레임용 버퍼

# ── 제스처 판별 함수 ────────────────────────────────────
def detect_gesture(lm: np.ndarray) -> str:
    """
    lm: (21,3) ndarray — Mediapipe 손 랜드마크
    반환: "Pinch" | "OpenHand" | "Fist" | "Unknown"
    """
    wrist = lm[0]
    # 손목→팁, 손목→PIP/기준 거리들
    d04 = np.linalg.norm(wrist - lm[4])   # 엄지 팁
    d03 = np.linalg.norm(wrist - lm[3])   # 엄지 PIP
    d08 = np.linalg.norm(wrist - lm[8])   # 검지 팁
    d06 = np.linalg.norm(wrist - lm[6])   # 검지 PIP
    d012 = np.linalg.norm(wrist - lm[12]) # 중지 팁
    d010 = np.linalg.norm(wrist - lm[10]) # 중지 PIP
    d016 = np.linalg.norm(wrist - lm[16]) # 약지 팁
    d014 = np.linalg.norm(wrist - lm[14]) # 약지 PIP
    d020 = np.linalg.norm(wrist - lm[20]) # 소지 팁
    d018 = np.linalg.norm(wrist - lm[18]) # 소지 PIP


    # (손등/손바닥 구분) 손목→엄지 PIP 거리와 손목→검지 PIP 거리 비교
    thumb_folded    = (d04 < d03)
    index_folded    = (d08 < d06)
    middle_folded   = (d012 < d010)
    ring_folded     = (d016 < d014)
    pinky_folded    = (d020 < d018)

    thumb_unfolded    = (d04 > d03)
    index_unfolded    = (d08 > d06)
    middle_unfolded   = (d012 > d010)
    ring_unfolded     = (d016 > d014)
    pinky_unfolded    = (d020 > d018)
    # if thumb_folded and index_folded:
        # return "Pinch"

    # 2) 나머지 손가락 접힘 상태 리스트
    folded_All = [
        thumb_folded,   # 엄지
        index_folded,   # 검지
        middle_folded,  # 중지
        ring_folded,    # 약지
        pinky_folded,   # 소지
    ]

    folded_V = [
        thumb_folded,
        index_unfolded,
        middle_unfolded,  # 중지
        ring_folded,  # 약지
        pinky_folded,  # 소지
    ]

    # 3) 모두 접혀 있으면 Fist, 모두 펴져 있으면 OpenHand
    if all(folded_All):
        return "Fist"
    if all(folded_V):
        return "VSign"
    if not any(folded_All):
        return "OpenHand"

    return "Unknown"

# ── 웹캠 시작 ──────────────────────────────────────────────
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    raise RuntimeError("웹캠을 열 수 없습니다.")
print("[INFO] 카메라 연결 성공, 추적 시작")

try:
    while True:
        ok, frame = cap.read()
        if not ok: break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb)

        if res.multi_hand_landmarks:
            h, w, _ = frame.shape
            lm_now = np.array([[pt.x, pt.y, pt.z] for pt in res.multi_hand_landmarks[0].landmark],
                              dtype=np.float32)

            # --- EMA 스무딩 ------------------------------
            smooth_lms = lm_now if smooth_lms is None \
                         else SMOOTHING_ALPHA*lm_now + (1-SMOOTHING_ALPHA)*smooth_lms

            # --- 랜드마크 OSC 전송 -----------------------
            for i, (x, y, z) in enumerate(smooth_lms):
                osc_client.send_message(f"/hand/landmark/{i}", [float(x), float(y), float(z)])
                cv2.circle(frame, (int(x*w), int(y*h)), 4, (0,255,0), -1)
                cv2.putText(frame, str(i), (int(x*w)+4, int(y*h)-4),
                            cv2.FONT_HERSHEY_PLAIN, .7, (255,0,0), 1)

            # --- 제스처 계산 & 전송 -----------------------
            gesture = detect_gesture(smooth_lms)
            osc_client.send_message("/hand/gesture", gesture)

            # (옵션) 랜드마크 연결선 그리기
            mp_drawing.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)

        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release(); cv2.destroyAllWindows(); hands.close()
    print("[INFO] 종료")