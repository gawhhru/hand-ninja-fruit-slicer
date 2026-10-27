# Hand Ninja 🍎⭐💣

Game chém trái cây điều khiển bằng **đầu ngón trỏ** qua webcam, dùng MediaPipe HandLandmarker + OpenCV.

## Luật chơi
| Vật thể | Kết quả |
|---|---|
| Apple | +1 điểm |
| Star | +5 điểm |
| Bomb | -1 HP (có 3 HP, hết HP là thua) |

- Cứ mỗi 10 điểm lên 1 level (tối đa level 10): vật bay nhanh hơn, ra dày hơn, nhiều bomb hơn.
- Điểm cao nhất được lưu vào `highscore.json`.

## Cài đặt
Yêu cầu Python 3.9+ và có webcam. Lần chạy đầu game tự tải model `models/hand_landmarker.task` (cần internet).

```bash
pip install -r requirements.txt
python main.py
```

## Cách chơi
1. Giơ tay trước camera, vẫy nhanh ngón trỏ để chém.
2. Chém vòng tròn xanh "START" để bắt đầu.
3. Chỉ đưa tay chạm vào vật mà không vẫy nhanh thì **không** tính là chém.
4. Phím: `SPACE` bắt đầu / chơi lại (khi đang ở màn hình chờ hoặc Game Over), `Q` hoặc `ESC` thoát.

## Cấu trúc project
| File | Vai trò |
|---|---|
| `main.py` | Camera, gọi MediaPipe, vẽ giao diện |
| `game_logic.py` | **Thuật toán và luật game** (không phụ thuộc camera): làm mượt, vận tốc, va chạm, điểm, HP, level, highscore |
| `test_game_logic.py` | Unit test cho `game_logic.py` |

Chạy test (không cần webcam):
```bash
python -m unittest -v
```

## Thuật toán chính
1. **MediaPipe Hands** -> toạ độ landmark 8 (đầu ngón trỏ).
2. **Làm mượt** bằng trung bình trượt mũ (EMA) để giảm rung.
3. **Vận tốc** = quãng đường giữa 2 frame / dt; chỉ tính là chém khi vận tốc >= ngưỡng.
4. **Va chạm**: khoảng cách từ tâm vật đến đoạn thẳng (vị trí frame trước -> frame hiện tại) <= bán kính.
5. **Luật game**: cộng điểm / trừ HP / lên level / lưu highscore.
6. **Độ khó**: level tăng thì tốc độ game, tần suất ra vật và tỉ lệ bomb đều tăng.

## Demo
(Thêm link video demo ở đây)
