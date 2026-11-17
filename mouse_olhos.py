import argparse
import ctypes
import os
from pathlib import Path
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
import pyautogui

from gaze import EyeController, eye_position

MODEL = Path(__file__).resolve().parent / 'models' / 'face_landmarker.task'
MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/'
             'face_landmarker/face_landmarker/float16/1/face_landmarker.task')
WINDOW = 'IAMouse - olhar'


def download_model():
    if MODEL.exists():
        return MODEL
    print('Baixando modelo do MediaPipe (somente na primeira execucao)...')
    MODEL.parent.mkdir(exist_ok=True)
    temporary = MODEL.with_suffix('.download')
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
            with temporary.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        temporary.replace(MODEL)
    finally:
        temporary.unlink(missing_ok=True)
    return MODEL


class Keys:
    def __init__(self):
        self.previous = set()

    def read(self):
        local = cv2.waitKey(1) & 0xFF
        pressed = set()
        if os.name == 'nt':
            for code, name in [(27, 'exit'), (119, 'pause'), (120, 'calibrate'),
                               (32, 'sample')]:
                if ctypes.windll.user32.GetAsyncKeyState(code) & 0x8000:
                    pressed.add(name)
        events = pressed - self.previous
        self.previous = pressed
        mapping = {27: 'exit', ord('q'): 'exit', ord('p'): 'pause',
                   ord('c'): 'calibrate', 32: 'sample'}
        if local in mapping:
            events.add(mapping[local])
        return events


def label(frame, text, row=0, color=(230, 230, 230)):
    cv2.putText(frame, text, (20, 32 + row * 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, color, 2, cv2.LINE_AA)


def draw_eyes(frame, landmarks):
    height, width = frame.shape[:2]
    for indices, iris in [([33, 160, 158, 133, 153, 144], 468),
                          ([362, 385, 387, 263, 373, 380], 473)]:
        contour = np.array([(int(landmarks[i].x * width), int(landmarks[i].y * height))
                            for i in indices], dtype=np.int32)
        cv2.polylines(frame, [contour], True, (0, 255, 0), 1, cv2.LINE_AA)
        center = (int(landmarks[iris].x * width), int(landmarks[iris].y * height))
        cv2.circle(frame, center, 3, (0, 255, 255), -1)
    points = np.array([(p.x * width, p.y * height) for p in landmarks])
    eye_points = points[[33, 133, 362, 263, 159, 145, 386, 374]]
    low = np.maximum(eye_points.min(axis=0).astype(int) - [20, 15], 0)
    high = np.minimum(eye_points.max(axis=0).astype(int) + [20, 15], [width, height])
    crop = frame[low[1]:high[1], low[0]:high[0]].copy()
    return cv2.resize(crop, (360, 100)) if crop.size else None


def run(camera, sensitivity=1.0):
    if os.name == 'nt':
        ctypes.windll.user32.SetProcessDPIAware()
    screen = np.array(pyautogui.size(), dtype=float)
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.01
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(download_model())),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_faces=1, min_face_detection_confidence=0.6,
        min_tracking_confidence=0.6)
    cap = cv2.VideoCapture(camera)
    try:
        if not cap.isOpened():
            raise RuntimeError('Webcam indisponivel. Feche outros apps ou use --camera 1.')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        keys = Keys()
        controller = EyeController(sensitivity)
        paused = True
        capture_start = None
        collected = []
        remainder = np.zeros(2)
        message = 'Olhe ao centro do monitor e pressione ESPACO para calibrar.'
        last_time, timestamp = time.monotonic(), -1
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, 800, 600)
        cv2.moveWindow(WINDOW, 80, 80)
        with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
            while True:
                events = keys.read()
                if 'exit' in events or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
                if 'calibrate' in events or ('sample' in events and controller.center is None):
                    paused, capture_start, collected = True, time.monotonic(), []
                    controller.filtered = None
                if 'pause' in events and controller.center is not None and capture_start is None:
                    paused = not paused
                    controller.filtered = None
                    remainder[:] = 0
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError('A webcam parou de enviar imagens.')
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now = time.monotonic()
                dt = min(now - last_time, 0.05)
                last_time = now
                timestamp = max(timestamp + 1, int(now * 1000))
                result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                           data=rgb), timestamp)
                gaze, eye_zoom = None, None
                if result.face_landmarks:
                    landmarks = result.face_landmarks[0]
                    gaze = eye_position(landmarks, frame.shape[1], frame.shape[0])
                    eye_zoom = draw_eyes(frame, landmarks)
                if capture_start is not None:
                    message = 'Calibrando: olhe ao centro do monitor por 3 segundos.'
                    if now - capture_start >= 0.8 and gaze is not None:
                        collected.append(gaze)
                    if now - capture_start >= 3:
                        capture_start = None
                        try:
                            controller.calibrate(collected)
                            message = 'Centro salvo. F8 ativa. Olhar ao centro para o cursor.'
                        except ValueError as exc:
                            message = str(exc) + ' F9: repetir.'
                velocity = controller.velocity(gaze if not paused else None, dt)
                if not paused and gaze is not None:
                    step = velocity * dt + remainder
                    pixels = np.trunc(step)
                    remainder = step - pixels
                    if np.any(pixels):
                        target = np.clip(np.array(pyautogui.position()) + pixels, 2, screen - 3)
                        pyautogui.moveTo(int(target[0]), int(target[1]))
                else:
                    remainder[:] = 0
                canvas = np.zeros((600, 800, 3), dtype=np.uint8)
                canvas[:450] = cv2.resize(frame, (800, 450))
                cv2.rectangle(canvas, (0, 0), (800, 112), (20, 20, 20), -1)
                status = 'PAUSADO - F8 ativa' if paused else 'MOUSE DO PC - CONTROLADO PELAS IRIS'
                if gaze is None:
                    status += ' | Olhos nao detectados'
                label(canvas, status, color=(0, 220, 255))
                label(canvas, message, 1)
                label(canvas, 'F8: pausar | F9: calibrar centro | ESC: sair', 2)
                if eye_zoom is not None:
                    canvas[480:580, 20:380] = eye_zoom
                cv2.putText(canvas, 'IRIS: pontos amarelos', (20, 470),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                origin = (590, 525)
                cv2.circle(canvas, origin, 50, (80, 80, 80), 1)
                endpoint = tuple((np.array(origin) + velocity / 1100 * 45).astype(int))
                cv2.arrowedLine(canvas, origin, endpoint, (0, 255, 255), 3)
                cv2.putText(canvas, 'Direcao do cursor', (500, 595),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(WINDOW, canvas)
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Controle do mouse pelo olhar usando uma webcam.')
    parser.add_argument('--camera', type=int, default=0, help='Indice da webcam (padrao: 0)')
    parser.add_argument('--sensibilidade', type=float, default=1.0, help='Ganho do olhar (padrao: 1.0)')
    args = parser.parse_args()
    if not 0.1 <= args.sensibilidade <= 5:
        parser.error('--sensibilidade deve estar entre 0.1 e 5')
    try:
        run(args.camera, args.sensibilidade)
    except (KeyboardInterrupt, pyautogui.FailSafeException):
        print('\nControle encerrado.')
    except (RuntimeError, OSError, ValueError) as exc:
        parser.exit(1, f'Erro: {exc}\n')


if __name__ == '__main__':
    main()
