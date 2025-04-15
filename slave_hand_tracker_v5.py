# slave_server.py를 변형함 손 트래킹 코드 추가
# v2는 마스터에서 밀려오는 프레임을 순차적으로 계속 처리하느라 병목이 생김
# 병목을 방지하고자 응답 통신으로 개선

import cv2
import numpy as np
import socket
import mediapipe as mp

# Mediapipe Hands 초기화
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False,
                       max_num_hands=1,
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

HOST = ''
PORT = 9999

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"[INFO] 슬레이브: 서버 시작, 포트 {PORT}")

conn, addr = server_socket.accept()
print(f"[INFO] 연결됨: {addr}")

data = b""
payload_size = 4

while True:
    while len(data) < payload_size:
        packet = conn.recv(4096)
        if not packet:
            break
        data += packet

    if len(data) < payload_size:
        break

    packed_size = data[:payload_size]
    data = data[payload_size:]
    frame_size = int.from_bytes(packed_size, byteorder='big')

    while len(data) < frame_size:
        packet = conn.recv(4096)
        if not packet:
            break
        data += packet

    frame_data = data[:frame_size]
    data = data[frame_size:]

    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        print("[WARN] 프레임 디코딩 실패")
        continue

    # Mediapipe 손 인식 처리
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = hands.process(image_rgb)
    image_rgb.flags.writeable = True

    # 랜드마크가 있으면 그리기
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # 프레임 표시
    cv2.imshow("Slave Received", frame)

    # ACK 응답
    conn.sendall(b'OK')

    # 결과 화면 출력
    cv2.imshow("Slave: Hand Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

conn.close()
server_socket.close()
cv2.destroyAllWindows()
