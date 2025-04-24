# hand_tracker_v1.py
# 손 추적 및 OSC 전송
# 추가적으로 언리얼엔진에서 데이터를 받아서 손 모델을 실시간 조작하는 프로젝트
# ────────────────────────────────────────────────────────────────

import cv2
import numpy as np
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient

# ─── 설정 ─────────────────────────────────────────────────────────
# 언리얼 에디터에서 OSCServer 생성 시 지정한 포트와 IP
UNREAL_IP   = "127.0.0.1"
UNREAL_PORT = 8000

SMOOTHING_ALPHA  = 0.4  # 0.0 ~ 1.0, 클수록 부드러움↑ 반응속도↓

# ─── OSC 클라이언트 초기화 ───────────────────────────────────────
osc_client = SimpleUDPClient(UNREAL_IP, UNREAL_PORT)
print(f"[INFO] OSC client → {UNREAL_IP}:{UNREAL_PORT}")

# ─── MediaPipe Hands 초기화 ──────────────────────────────────────
mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# ─── smoothing 버퍼 준비 ──────────────────────────────────────────
smooth_lms = None  # first-frame 초기화 용


# ─── 웹캠 열기 ────────────────────────────────────────────────────
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    raise RuntimeError("웹캠을 열 수 없습니다.")

print("[INFO] 카메라 연결 성공, 추적을 시작합니다.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # BGR→RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results   = hands.process(frame_rgb)

        # 랜드마크가 하나라도 검출되면
        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0]

            h, w, _ = frame.shape

            # 1) current landmarks 배열(21×3) 생성
            current = np.array(
                [[pt.x, pt.y, pt.z] for pt in lm.landmark],
                dtype=np.float32
            )

            # 2) EMA 스무딩
            if smooth_lms is None:
                smooth_lms = current.copy()
            else:
                smooth_lms = SMOOTHING_ALPHA * current + (1 - SMOOTHING_ALPHA) * smooth_lms

            # 3) 스무딩된 값으로 Draw & OSC 전송
            for idx, (x, y, z) in enumerate(smooth_lms):
                cx, cy = int(x * w), int(y * h)

                # 화면 디버그 표시
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.putText(frame, str(idx), (cx + 5, cy - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

                # OSC 전송
                address = f"/hand/landmark/{idx}"
                osc_client.send_message(address, [float(x), float(y), float(z)])


            # # 21개 포인트 순회
            # for idx, pt in enumerate(lm.landmark):

            #     # 이미지 위 좌표로 변환
            #     x = int(pt.x * w)
            #     y = int(pt.y * h)
            #     cx, cy = int(pt.x * w), int(pt.y * h)

            #     cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
            #     cv2.putText(frame, str(idx), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            #     # OSC 주소: /hand/landmark/0 ~ /hand/landmark/20
            #     address = f"/hand/landmark/{idx}"
            #     # 세 개의 float 리스트로 전송
            #     osc_client.send_message(address, [pt.x, pt.y, pt.z])

            # 랜드마크 그리기 (옵션)
            mp_drawing.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
            



        # 프레임 표시 (옵션)
        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("[INFO] 종료합니다.")
