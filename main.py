"""
Pipeline:
    Camera -> MediaPipe Hands (landmark 8)
           -> game_logic.py
           -> main.py 
"""

import math
import os
import random
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import game_logic as gl

W, H = 960, 540
FINGER_TIP = 8               

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "hand_landmarker.task")
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.json")


def ensure_model():
    """Tải model nhận diện tay nếu chưa có (chỉ tải 1 lần)."""
    if os.path.exists(MODEL_PATH):
        return
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print("Downloading hand_landmarker.task model (~7.5MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download complete.")


def create_landmarker():
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def put_center(img, text, y, scale, color, thick=3):
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    cv2.putText(img, text, (W // 2 - tw // 2, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thick, cv2.LINE_AA)


def draw_item(img, it):
    c = (int(it.x), int(it.y))
    r = int(it.r)
    if it.kind == gl.APPLE:
        cv2.circle(img, c, r, (40, 40, 220), -1, cv2.LINE_AA)
        cv2.circle(img, c, r, (20, 20, 140), 2, cv2.LINE_AA)
        cv2.circle(img, (c[0] - r // 3, c[1] - r // 3), r // 4, (140, 140, 255), -1, cv2.LINE_AA)
        cv2.line(img, (c[0], c[1] - r), (c[0] + 4, c[1] - r - 12), (30, 90, 40), 3, cv2.LINE_AA)
        cv2.ellipse(img, (c[0] + 12, c[1] - r - 6), (10, 5), -30, 0, 360, (60, 190, 70), -1, cv2.LINE_AA)
    elif it.kind == gl.STAR:
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5 + it.angle
            rad = r if i % 2 == 0 else r * 0.45
            pts.append([c[0] + rad * math.cos(ang), c[1] + rad * math.sin(ang)])
        pts = np.array(pts, np.int32)
        cv2.fillPoly(img, [pts], (0, 215, 255), cv2.LINE_AA)
        cv2.polylines(img, [pts], True, (0, 140, 200), 2, cv2.LINE_AA)
    elif it.kind == gl.BOMB:
        cv2.circle(img, c, r, (35, 35, 35), -1, cv2.LINE_AA)
        cv2.circle(img, c, r, (90, 90, 90), 2, cv2.LINE_AA)
        cv2.circle(img, (c[0] - r // 3, c[1] - r // 3), r // 5, (110, 110, 110), -1, cv2.LINE_AA)
        cv2.line(img, (c[0], c[1] - r), (c[0] + 8, c[1] - r - 14), (150, 150, 150), 3, cv2.LINE_AA)
        cv2.circle(img, (c[0] + 8, c[1] - r - 16), 5, (0, 140, 255), -1, cv2.LINE_AA)
    elif it.kind == gl.START:
        cv2.circle(img, c, r, (60, 180, 60), -1, cv2.LINE_AA)
        cv2.circle(img, c, r, (255, 255, 255), 3, cv2.LINE_AA)
        (tw, th), _ = cv2.getTextSize(it.label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.putText(img, it.label, (c[0] - tw // 2, c[1] + th // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (255, 255, 255), 2, cv2.LINE_AA)


def draw_blade(img, blade, now):
    pts = list(blade.trail)
    for i in range(1, len(pts)):
        k = max(0.0, 1 - (now - pts[i][2]) / gl.TRAIL_LIFETIME)
        cv2.line(img, (int(pts[i - 1][0]), int(pts[i - 1][1])), (int(pts[i][0]), int(pts[i][1])),
                 (255, 255, 255), max(1, int(10 * k)), cv2.LINE_AA)
    if blade.pos is not None:
        cv2.circle(img, (int(blade.pos[0]), int(blade.pos[1])), 8, (0, 255, 255), -1, cv2.LINE_AA)


class Effects:
    def __init__(self):
        self.particles, self.texts = [], []
        self.flash = 0.0
        self.banner = 0.0
        self.banner_text = ""

    def burst(self, x, y, color, n=14):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(120, 420)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s, 0.5, color])

    def handle(self, ev):
        name, x, y, val = ev
        if name == gl.APPLE:
            self.burst(x, y, (60, 60, 255))
            self.texts.append([f"+{val}", x, y, 0.8, (60, 60, 255)])
        elif name == gl.STAR:
            self.burst(x, y, (0, 215, 255))
            self.texts.append([f"+{val}", x, y, 0.8, (0, 215, 255)])
        elif name == gl.BOMB:
            self.flash = 0.35
            self.burst(x, y, (80, 80, 80), 20)
            self.texts.append(["-1 HP", x, y, 0.9, (0, 0, 255)])
        elif name == "levelup":
            self.banner = 1.5
            self.banner_text = f"LEVEL {val}!"

    def update(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 600 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.texts:
            t[2] -= 60 * dt
            t[3] -= dt
        self.texts = [t for t in self.texts if t[3] > 0]
        self.flash = max(0.0, self.flash - dt)
        self.banner = max(0.0, self.banner - dt)

    def draw(self, img):
        for p in self.particles:
            cv2.circle(img, (int(p[0]), int(p[1])), 4, p[5], -1)
        for t in self.texts:
            cv2.putText(img, t[0], (int(t[1]), int(t[2])), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, t[4], 3, cv2.LINE_AA)
        if self.flash > 0:
            overlay = np.zeros_like(img)
            overlay[:] = (0, 0, 255)
            cv2.addWeighted(overlay, 0.35 * (self.flash / 0.35), img, 1, 0, img)
        if self.banner > 0:
            put_center(img, self.banner_text, H // 2, 2.0, (0, 255, 255), 4)


def draw_hud(img, game):
    cv2.putText(img, f"Score: {game.score}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, f"Best: {game.highscore}", (20, 75), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, f"Level {game.level}", (W // 2 - 60, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (0, 255, 0), 2, cv2.LINE_AA)
    for i in range(gl.MAX_HP):                      
        x0 = W - 40 - (gl.MAX_HP - i) * 50
        col = (0, 0, 230) if i < game.hp else (70, 70, 70)
        cv2.rectangle(img, (x0, 20), (x0 + 40, 44), col, -1)
        cv2.rectangle(img, (x0, 20), (x0 + 40, 44), (255, 255, 255), 2)

    if game.state == gl.WAITING:
        put_center(img, "HAND NINJA", 130, 1.8, (255, 255, 255))
        put_center(img, "Slice with your index finger!", 180, 0.9, (255, 255, 255))
        put_center(img, "Apple +1   Star +5   Bomb -1 HP", 215, 0.8, (0, 255, 255))
        put_center(img, "Press SPACE (or slice START) to play   |   Q / ESC to quit", H - 30, 0.7, (255, 255, 255))
    elif game.state == gl.GAME_OVER:
        put_center(img, "GAME OVER", 120, 1.8, (0, 0, 255))
        put_center(img, f"Score: {game.score}   Best: {game.highscore}", 170, 0.9, (255, 255, 255))
        if game.new_record:
            put_center(img, "NEW RECORD!", 205, 0.9, (0, 255, 255))
        put_center(img, "Press SPACE to play again   |   Q / ESC to quit", H - 30, 0.7, (255, 255, 255))


def main():
    ensure_model()
    landmarker = create_landmarker()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Cannot open the camera. Check if it is connected and not used by another app.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    game = gl.SliceGame(W, H, highscore=gl.load_highscore(HIGHSCORE_FILE))
    blade = gl.Blade()
    fx = Effects()
    prev_time = start_time = time.time()
    last_ts = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)                     
        frame = cv2.resize(frame, (W, H))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts = int((time.time() - start_time) * 1000)
        if ts <= last_ts:
            ts = last_ts + 1                          
        last_ts = ts
        result = landmarker.detect_for_video(mp_image, ts)
        tip = None
        if result.hand_landmarks:
            lm = result.hand_landmarks[0][FINGER_TIP]
            tip = (lm.x * W, lm.y * H)

        now = time.time()
        dt = min(now - prev_time, 0.05)
        prev_time = now
        blade.update(tip, dt, now)
        game.update(dt, blade)
        for ev in game.pop_events():
            fx.handle(ev)
            if ev[0] == "gameover":
                gl.save_highscore(HIGHSCORE_FILE, game.highscore)
        fx.update(dt)

        frame = cv2.addWeighted(frame, 0.55, np.zeros_like(frame), 0.45, 0)  
        for it in game.items:
            draw_item(frame, it)
        fx.draw(frame)
        draw_hud(frame, game)
        draw_blade(frame, blade, now)
        cv2.imshow("Hand Ninja", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        if key == ord(" ") and game.state != gl.PLAYING:  
            game.start()
        if key == ord("r"):
            game.start()

    cap.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
