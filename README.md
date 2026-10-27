# Hand Ninja 🍎⭐💣

A fruit-slicing game controlled by the **index fingertip** via webcam, powered by MediaPipe HandLandmarker and OpenCV.

## Rules

| Object | Outcome |
| --- | --- |
| Apple | +1 point |
| Star | +5 points |
| Bomb | -1 HP (Starts with 3 HP; 0 HP results in Game Over) |

* Every 10 points increases the level (up to level 10): objects move faster, spawn more densely, and include more bombs.
* High scores are saved to `highscore.json`.

## Installation

Requires Python 3.9+ and a webcam. On the first run, the game will automatically download the model `models/hand_landmarker.task` (internet connection required).

```bash
pip install -r requirements.txt
python main.py

```

## How to Play

1. Raise your hand in front of the camera and swipe quickly with your index finger to slice.
2. Slice the blue "START" circle to begin.
3. Simply touching an object without a fast swipe will **not** count as a slice.
4. Controls: `SPACE` to start / restart (on the start screen or Game Over screen), `Q` or `ESC` to quit.

## Project Structure

| File | Role |
| --- | --- |
| `main.py` | Handles camera input, calls MediaPipe, and renders the UI |
| `game_logic.py` | **Core algorithms and game rules** (camera-independent): smoothing, velocity, collision detection, score, HP, level, and high score management |
| `test_game_logic.py` | Unit tests for `game_logic.py` |

Run tests (no webcam required):

```bash
python -m unittest -v

```

## Core Algorithms

1. **MediaPipe Hands** $\rightarrow$ Extracts landmark 8 (index fingertip) coordinates.


2. **Smoothing** via Exponential Moving Average (EMA) to reduce jitter.
3. **Velocity** = distance between 2 frames / dt; a slice is registered only when velocity >= threshold.
4. **Collision Detection**: Distance from the object's center to the line segment (previous frame position $\rightarrow$ current frame position) <= radius.
5. **Game Logic**: Score addition / HP deduction / level progression / high score persistence.
6. **Difficulty Scaling**: As the level increases, game speed, spawn rate, and bomb frequency all scale up.

## Demo

...work in progress...
