# 🖐 Raspberry Pi Hand Tracking System (Master/Slave)

실시간 USB 카메라 입력을 기반으로, **두 대의 라즈베리파이를 연결하여 손 추적을 수행**하는 저사양 최적화 시스템입니다.  
마스터는 카메라로 입력을 받아 슬레이브에 전송하고, 슬레이브는 딥러닝 추론을 수행하여 손의 랜드마크를 인식합니다.

---

## 📦 시스템 구성

| 역할 | 기기 | 사양 | 용도 |
|------|------|------|------|
| 마스터 | Raspberry Pi 4 Model B (8GB RAM) | Ubuntu 22.04 | USB 카메라 연결, 영상 전송 |
| 슬레이브 | Raspberry Pi 4 Model B (2GB RAM) | Ubuntu 22.04 | 영상 수신, 손 마디 추적 및 분석 |

> ⚙️ 기기 간 직접 이더넷 연결 + 고정 IP 구성 (인터넷 유지 가능)

*인터넷 무선 연결을하니 인터넷 문제시 지연 발생*

---

## 📌 마스터 역할

- USB 카메라로 프레임 캡처
- 슬레이브로부터 `OK` 응답을 받고 다음 프레임 전송

---

## 📌 슬레이브 역할

- palm detection 수행 (손 위치 인식)
- ROI 영역 확인
- `hand_landmark_lite.tflite` 모델로 손 마디 21점 추적
- 디버깅 또는 GUI 출력 (선택)
- `OK` 응답 전송하여 병목 방지

---

## 📦 사용 모델

- `models/palm_detection_lite.tflite`
- `models/hand_landmark_lite.tflite`

> 두 모델 모두 `MediaPipe`에서 제공하는 TFLite Runtime 전용 Lite 모델

---

## 🔧 우분투 초기 설정 (공통)

### 1. Python 3.9 설치

```bash
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev
```

### 2. 가상환경 구성

```bash
python3.9 -m venv masterenv   # 슬레이브는 slaveenv
source masterenv/bin/activate
```

---

## 📦 패키지 설치

### 마스터

```bash
pip install mediapipe
```

### 슬레이브

```bash
pip install mediapipe
pip install opencv-python numpy tflite-runtime
```

---

## 📂 프로젝트 디렉토리 구조(제작자 개인 구조)

```
project/
│
├── master_client.py           # 마스터 전송 스크립트
├── slave_hand_tracker_v5.py   # 슬레이브 손 추적 스크립트
├── models/
│   ├── palm_detection_lite.tflite
│   └── hand_landmark_lite.tflite
└── config/
    └── slave_ip.txt           # 슬레이브 IP 저장용 파일
```

---

## 🌐 네트워크 구성 (이더넷 직접 연결)

### 고정 IP 할당 (부팅 시 자동 설정)

#### `set_eth0_static.sh 작성`

```bash 
sudo nano /usr/local/bin/set_eth0_static.sh
```

#### 아래 내용 작성

```bash
#!/bin/bash
sudo ip addr flush dev eth0
sudo ip addr add 192.168.50.2/24 dev eth0  # 마스터는 .2, 슬레이브는 .3 으로 ip 할당
sudo ip link set eth0 up
```

#### crontab 등록

```bash
sudo crontab -e
# 실행 후 맨 아래에 추가
@reboot bash /usr/local/bin/set_eth0_static.sh
```

---

## ▶️ 실행 방법

### 마스터

```bash
source masterenv/bin/activate
python master_client.py
```

### 슬레이브

```bash
source slaveenv/bin/activate
python slave_hand_tracker_v5.py
```

---

## 📌 주요 특징

- 초경량 모델 기반 실시간 손 추적 (Lite TFLite 사용)
- 프레임 단위 ACK 기반 통신으로 병목 방지
- 영상 전송과 추론 작업 분리로 성능 분산
- 해상도 축소, ROI 전송 등으로 처리 최소화

---

## 📈 향후 개선 아이디어

- 슬레이브 추론 결과를 마스터로 되돌려 표시
- YOLO 기반 다수 손 검출
- 손 모양 분류 또는 제스처 인식 기능 추가
- UDP 전송 또는 gRPC 최적화 가능성 검토
- 슬레이브 기기의 한계가 명확하니 더 개선된 기기를 사용 고려(현 상태도 딜레이 존재)

---

## 🧠 참고

- MediaPipe Hands: https://google.github.io/mediapipe/solutions/hands
- TFLite Runtime: https://www.tensorflow.org/lite/guide/python
