# master_client.py
import socket
import cv2

SLAVE_IP = '192.168.170.165'  # 슬레이브 IP 주소
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SLAVE_IP, PORT))

cap = cv2.VideoCapture(0)
print("[INFO] 마스터 시작")
print("[INFO] 마스터: 영상 전송 시작")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 사이즈 조정
    # frame = cv2.resize(frame, (160, 120))

    # 프레임 JPEG 인코딩, 압축률 조정함
    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
    data = buffer.tobytes()

    # 데이터 크기 전송 (4바이트)
    size = len(data).to_bytes(4, byteorder='big')
    client_socket.sendall(size + data)

    # 슬레이브 응답 대기 (ACK)
    ack = client_socket.recv(2)
    if ack != b'OK':
        print("[WARN] 슬레이브 ACK 누락 또는 지연")

    cv2.imshow("Master Sending", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
client_socket.close()
cv2.destroyAllWindows()
