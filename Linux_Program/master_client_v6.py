# master_client.py
import socket
import cv2
import struct
import numpy as np

with open("slave_ip.txt") as f:
    SLAVE_IP = f.read().strip()
PORT = 9999

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SLAVE_IP, PORT))
print("[MASTER] Connected to slave", SLAVE_IP)

cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # ── 프레임 인코딩 & 전송 ──────────────────────────────────────────────────
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
    data = buf.tobytes()
    sock.sendall(struct.pack(">I", len(data)) + data)

    # ── 결과 수신 ────────────────────────────────────────────────────────────
    flag = sock.recv(1)
    if not flag: break
    if flag == b"\x01":
        lm_bytes = sock.recv(63 * 4)     # 21×3 float32
        lms = np.frombuffer(lm_bytes, np.float32).reshape(-1, 3)

        # 2D 좌표로 변환(화면 해상도 곱)
        h, w = frame.shape[:2]
        pts = (lms[:, :2] * [w, h]).astype(int)
        for x, y in pts:
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

    cv2.imshow("Master View", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release(); sock.close(); cv2.destroyAllWindows()