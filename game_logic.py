"""
    - dist_point_segment : khoảng cách điểm - đoạn thẳng (dùng cho va chạm)
    - Blade              : làm mượt đầu ngón tay, tính vận tốc, lưu vệt chém
    - Item               : vật thể bay (apple / star / bomb / nút start)
    - SliceGame          : luật game (điểm, HP, level, highscore, sinh vật thể)
    - các hàm độ khó theo level
"""

import json
import math
import os
import random
from collections import deque

APPLE, STAR, BOMB, START = "apple", "star", "bomb", "start"
WAITING, PLAYING, GAME_OVER = "waiting", "playing", "game_over"

POINTS = {APPLE: 1, STAR: 5}

MAX_HP = 3
LEVEL_STEP = 10              
MAX_LEVEL = 10
GRAVITY = 1100                 

SMOOTH_ALPHA = 0.6             
MIN_SLICE_SPEED = 450          
HIT_MARGIN = 8                 
TRAIL_LIFETIME = 0.25          


def dist_point_segment(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    ab2 = abx * abx + aby * aby
    if ab2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * abx + (py - ay) * aby) / ab2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby))


def level_for_score(score):
    return min(MAX_LEVEL, score // LEVEL_STEP + 1)


def timescale(level):
    return 1.0 + 0.06 * (level - 1)


def spawn_interval(level):
    return max(0.35, 1.3 - 0.1 * (level - 1))


def bomb_prob(level):
    return min(0.35, 0.12 + 0.03 * (level - 1))


def burst_size(level):
    return 1 + level // 3


def load_highscore(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(json.load(f).get("highscore", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def save_highscore(path, score):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"highscore": int(score)}, f)
    except OSError:
        pass


class Blade:
    def __init__(self, smooth_alpha=SMOOTH_ALPHA):
        self.alpha = smooth_alpha
        self.pos = None
        self.prev = None
        self.speed = 0.0
        self.trail = deque() 

    def update(self, tip, dt, now):
        if tip is None:
            self.pos = None
            self.prev = None
            self.speed = 0.0
        else:
            if self.pos is None:
                new = tip
                self.prev = None
            else:
                new = (self.alpha * tip[0] + (1 - self.alpha) * self.pos[0],
                       self.alpha * tip[1] + (1 - self.alpha) * self.pos[1])
                self.prev = self.pos
            self.pos = new
            if self.prev is not None and dt > 0:
                self.speed = math.hypot(new[0] - self.prev[0], new[1] - self.prev[1]) / dt
            else:
                self.speed = 0.0
            self.trail.append((new[0], new[1], now))
        while self.trail and now - self.trail[0][2] > TRAIL_LIFETIME:
            self.trail.popleft()

    def is_slicing(self):
        return self.prev is not None and self.pos is not None and self.speed >= MIN_SLICE_SPEED


class Item:
    def __init__(self, kind, x, y, vx=0.0, vy=0.0, r=35, rng=random):
        self.kind = kind
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.r = r
        self.angle = rng.uniform(0, math.pi)
        self.spin = rng.uniform(-3, 3)
        self.label = ""

    def update(self, dt):
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt

    def is_gone(self, height):
        return self.y - self.r > height and self.vy > 0


class SliceGame:
    def __init__(self, width, height, highscore=0, rng=None):
        self.w, self.h = width, height
        self.rng = rng or random.Random()
        self.highscore = highscore
        self.new_record = False
        self.events = []
        self._reset_round()
        self._show_target("START")
        self.state = WAITING

    def _reset_round(self):
        self.score = 0
        self.hp = MAX_HP
        self.level = 1
        self.items = []
        self.spawn_timer = 0.8

    def _show_target(self, label):
        t = Item(START, self.w / 2, self.h / 2 + 40, r=70, rng=self.rng)
        t.spin = 0
        t.label = label
        self.items = [t]

    def start(self):
        self._reset_round()
        self.new_record = False
        self.state = PLAYING

    def _end_round(self):
        self.state = GAME_OVER
        if self.score > self.highscore:
            self.highscore = self.score
            self.new_record = True
        self.events.append(("gameover", 0, 0, self.score))
        self.items = []                 

    def pop_events(self):
        ev, self.events = self.events, []
        return ev

    def spawn_item(self):
        bp = bomb_prob(self.level)
        kind = self.rng.choices([BOMB, STAR, APPLE], weights=[bp, 0.10, 1 - bp - 0.10])[0]
        r = self.rng.randint(30, 40)
        x = self.rng.uniform(0.15 * self.w, 0.85 * self.w)
        peak = self.rng.uniform(0.45, 0.8) * self.h             
        vy = -math.sqrt(2 * GRAVITY * peak)
        target_x = self.rng.uniform(0.3 * self.w, 0.7 * self.w) 
        vx = (target_x - x) / (2 * abs(vy) / GRAVITY) * self.rng.uniform(0.6, 1.0)
        item = Item(kind, x, self.h + r, vx, vy, r, self.rng)
        self.items.append(item)
        return item

    def update(self, dt, blade):
        if blade.is_slicing():
            for it in list(self.items):
                if it not in self.items:
                    continue
                d = dist_point_segment((it.x, it.y), blade.prev, blade.pos)
                if d <= it.r + HIT_MARGIN:
                    self._on_slice(it)

        if self.state == PLAYING:
            gdt = dt * timescale(self.level)
            self.spawn_timer -= gdt
            if self.spawn_timer <= 0:
                for _ in range(self.rng.randint(1, burst_size(self.level))):
                    self.spawn_item()
                self.spawn_timer = spawn_interval(self.level) * self.rng.uniform(0.8, 1.2)
            for it in self.items:
                it.update(gdt)
            self.items = [it for it in self.items if not it.is_gone(self.h)]

    def _on_slice(self, it):
        if it.kind != START and self.state != PLAYING:
            return
        self.items.remove(it)
        if it.kind == START:
            self.start()
        elif it.kind in POINTS:
            gain = POINTS[it.kind]
            self.score += gain
            self.events.append((it.kind, it.x, it.y, gain))
            new_level = level_for_score(self.score)
            if new_level > self.level:
                self.level = new_level
                self.events.append(("levelup", it.x, it.y, new_level))
        elif it.kind == BOMB:
            self.hp -= 1
            self.events.append((BOMB, it.x, it.y, -1))
            if self.hp <= 0:
                self._end_round()
