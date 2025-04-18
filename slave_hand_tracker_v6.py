import cv2
import numpy as np
import socket
import mediapipe as mp

# ─── Mediapipe 초기화 ──────────────────────────────────────────────────────────
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(False, 1, 0.5, 0.5)
mp_draw = mp.solutions.drawing_utils

# ─── 네트워크 ─────────────────────────────────────────────────────────────────
HOST, PORT = "", 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT)); sock.listen(1)
conn, addr = sock.accept()
print(f"[SLAVE] Connected from {addr}")

buf, size_hdr = b"", 4

while True:
    # --- 프레임 길이 수신 ---
    while len(buf) < size_hdr:
        pkt = conn.recv(4096)
        if not pkt: break
        buf += pkt
    if len(buf) < size_hdr: break

    frame_len = struct.unpack(">I", buf[:size_hdr])[0]
    buf = buf[size_hdr:]

    # --- 프레임 본문 수신 ---
    while len(buf) < frame_len:
        pkt = conn.recv(4096)
        if not pkt: break
        buf += pkt
    frame_data, buf = buf[:frame_len], buf[frame_len:]

    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None: continue

    # ── 손 추론 ───────────────────────────────────────────────────────────────
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(image_rgb)
    has_hand = result.multi_hand_landmarks is not None

    # ── 결과 전송 : 1바이트 플래그 + 랜드마크(선택) ────────────────────────────
    if has_hand:
        lm = result.multi_hand_landmarks[0].landmark
        flat = np.array([[pt.x, pt.y, pt.z] for pt in lm], np.float32).flatten()
        payload = b"\x01" + flat.tobytes()           # 1(=True)
    else:
        payload = b"\x00"                            # 0(=False)
    conn.sendall(payload)

    # ── 시각화(선택) ──────────────────────────────────────────────────────────
    blank = np.zeros_like(frame)
    if has_hand:
        mp_draw.draw_landmarks(blank, result.multi_hand_landmarks[0],
                               mp_hands.HAND_CONNECTIONS, mp_draw.DrawingSpec(),
                               mp_draw.DrawingSpec())
    cv2.imshow("Slave", blank)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

conn.close(); sock.close(); cv2.destroyAllWindows()
