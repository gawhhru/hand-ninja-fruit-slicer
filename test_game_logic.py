import json
import os
import random
import tempfile
import unittest

import game_logic as gl

W, H = 960, 540


def fast_slice(game, x0=100, x1=220, y=100):
    blade = gl.Blade(smooth_alpha=1.0)
    blade.update((x0, y), 1 / 30, 0.0)
    blade.update((x1, y), 1 / 30, 1 / 30)
    game.update(1 / 30, blade)
    return blade


def make_playing_game(seed=1):
    g = gl.SliceGame(W, H, rng=random.Random(seed))
    g.start()
    g.items = []
    g.spawn_timer = 1e9
    return g


class TestGeometry(unittest.TestCase):
    def test_point_on_segment(self):
        self.assertAlmostEqual(gl.dist_point_segment((5, 0), (0, 0), (10, 0)), 0)

    def test_point_beside_segment(self):
        self.assertAlmostEqual(gl.dist_point_segment((5, 3), (0, 0), (10, 0)), 3)

    def test_point_beyond_end(self):
        self.assertAlmostEqual(gl.dist_point_segment((13, 4), (0, 0), (10, 0)), 5)

    def test_degenerate_segment(self):
        self.assertAlmostEqual(gl.dist_point_segment((3, 4), (0, 0), (0, 0)), 5)


class TestDifficulty(unittest.TestCase):
    def test_level_for_score(self):
        self.assertEqual(gl.level_for_score(0), 1)
        self.assertEqual(gl.level_for_score(9), 1)
        self.assertEqual(gl.level_for_score(10), 2)
        self.assertEqual(gl.level_for_score(10_000), gl.MAX_LEVEL)

    def test_difficulty_increases(self):
        for lv in range(1, gl.MAX_LEVEL):
            self.assertLess(gl.timescale(lv), gl.timescale(lv + 1))
            self.assertGreaterEqual(gl.spawn_interval(lv), gl.spawn_interval(lv + 1))
            self.assertLessEqual(gl.bomb_prob(lv), gl.bomb_prob(lv + 1))
        self.assertLessEqual(gl.bomb_prob(gl.MAX_LEVEL), 0.35)
        self.assertGreaterEqual(gl.spawn_interval(gl.MAX_LEVEL), 0.35)


class TestBlade(unittest.TestCase):
    def test_fast_move_is_slice(self):
        b = fast_slice(make_playing_game())
        self.assertTrue(b.is_slicing())

    def test_slow_move_is_not_slice(self):
        b = gl.Blade(smooth_alpha=1.0)
        b.update((100, 100), 1 / 30, 0.0)
        b.update((105, 100), 1 / 30, 1 / 30)
        self.assertFalse(b.is_slicing())

    def test_hand_lost_resets(self):
        b = gl.Blade(smooth_alpha=1.0)
        b.update((100, 100), 1 / 30, 0.0)
        b.update(None, 1 / 30, 1 / 30)
        self.assertFalse(b.is_slicing())
        self.assertIsNone(b.pos)


class TestScoring(unittest.TestCase):
    def test_apple_gives_1(self):
        g = make_playing_game()
        g.items = [gl.Item(gl.APPLE, 160, 100, r=30)]
        fast_slice(g)
        self.assertEqual(g.score, 1)
        self.assertEqual(g.items, [])

    def test_star_gives_5(self):
        g = make_playing_game()
        g.items = [gl.Item(gl.STAR, 160, 100, r=30)]
        fast_slice(g)
        self.assertEqual(g.score, 5)

    def test_bomb_costs_one_hp(self):
        g = make_playing_game()
        g.items = [gl.Item(gl.BOMB, 160, 100, r=30)]
        fast_slice(g)
        self.assertEqual(g.hp, gl.MAX_HP - 1)
        self.assertEqual(g.score, 0)
        self.assertEqual(g.state, gl.PLAYING)

    def test_item_far_away_not_hit(self):
        g = make_playing_game()
        g.items = [gl.Item(gl.APPLE, 160, 400, r=30)]
        fast_slice(g)
        self.assertEqual(g.score, 0)

    def test_slow_touch_does_not_score(self):
        g = make_playing_game()
        g.items = [gl.Item(gl.APPLE, 100, 100, r=30)]
        blade = gl.Blade(smooth_alpha=1.0)
        blade.update((95, 100), 1 / 30, 0.0)
        blade.update((100, 100), 1 / 30, 1 / 30)
        g.update(1 / 30, blade)
        self.assertEqual(g.score, 0)

    def test_three_bombs_game_over(self):
        g = make_playing_game()
        for _ in range(gl.MAX_HP):
            g.items = [gl.Item(gl.BOMB, 160, 100, r=30)]
            fast_slice(g)
        self.assertEqual(g.hp, 0)
        self.assertEqual(g.state, gl.GAME_OVER)
        self.assertIn("gameover", [e[0] for e in g.pop_events()])

    def test_no_scoring_after_game_over_in_same_frame(self):
        g = make_playing_game()
        g.hp = 1
        g.items = [gl.Item(gl.BOMB, 150, 100, r=30), gl.Item(gl.APPLE, 170, 100, r=30)]
        fast_slice(g)
        self.assertEqual(g.state, gl.GAME_OVER)
        self.assertEqual(g.score, 0)

    def test_level_up_event(self):
        g = make_playing_game()
        g.score = 9
        g.items = [gl.Item(gl.APPLE, 160, 100, r=30)]
        fast_slice(g)
        self.assertEqual(g.level, 2)
        self.assertIn("levelup", [e[0] for e in g.pop_events()])


class TestStateAndHighscore(unittest.TestCase):
    def test_slice_start_target_starts_game(self):
        g = gl.SliceGame(W, H, rng=random.Random(2))
        self.assertEqual(g.state, gl.WAITING)
        t = g.items[0]
        fast_slice(g, x0=t.x - 60, x1=t.x + 60, y=t.y)
        self.assertEqual(g.state, gl.PLAYING)
        self.assertEqual(g.score, 0)
        self.assertEqual(g.hp, gl.MAX_HP)

    def test_new_highscore_recorded(self):
        g = gl.SliceGame(W, H, highscore=3, rng=random.Random(3))
        g.start()
        g.items, g.spawn_timer, g.score, g.hp = [gl.Item(gl.BOMB, 160, 100, r=30)], 1e9, 12, 1
        fast_slice(g)
        self.assertEqual(g.state, gl.GAME_OVER)
        self.assertEqual(g.highscore, 12)
        self.assertTrue(g.new_record)

    def test_lower_score_keeps_highscore(self):
        g = gl.SliceGame(W, H, highscore=50, rng=random.Random(3))
        g.start()
        g.items, g.spawn_timer, g.score, g.hp = [gl.Item(gl.BOMB, 160, 100, r=30)], 1e9, 4, 1
        fast_slice(g)
        self.assertEqual(g.highscore, 50)
        self.assertFalse(g.new_record)

    def test_game_over_stays_until_space(self):
        g = gl.SliceGame(W, H, rng=random.Random(4))
        g.start()
        g.items, g.spawn_timer, g.score, g.hp = [gl.Item(gl.BOMB, 160, 100, r=30)], 1e9, 12, 1
        fast_slice(g)                              
        self.assertEqual(g.state, gl.GAME_OVER)
        self.assertEqual(g.items, [])                   
        fast_slice(g, x0=W / 2 - 100, x1=W / 2 + 100, y=H / 2 + 40)
        for _ in range(300):
            g.update(1 / 30, gl.Blade())
        self.assertEqual(g.state, gl.GAME_OVER)
        self.assertEqual(g.items, [])
        self.assertEqual(g.score, 12)

    def test_start_after_game_over_resets_round(self):
        g = gl.SliceGame(W, H, rng=random.Random(4))
        g.start()
        g.items, g.spawn_timer, g.score, g.hp, g.level = [gl.Item(gl.BOMB, 160, 100, r=30)], 1e9, 25, 1, 3
        fast_slice(g)
        self.assertEqual(g.state, gl.GAME_OVER)
        g.start()                                      
        self.assertEqual(g.state, gl.PLAYING)
        self.assertEqual((g.score, g.hp, g.level), (0, gl.MAX_HP, 1))

    def test_highscore_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hs.json")
            self.assertEqual(gl.load_highscore(path), 0)    
            gl.save_highscore(path, 42)
            self.assertEqual(gl.load_highscore(path), 42)
            with open(path, "w") as f:
                f.write("not json")
            self.assertEqual(gl.load_highscore(path), 0)     


class TestSpawning(unittest.TestCase):
    def test_spawned_items_valid(self):
        g = make_playing_game(seed=5)
        for _ in range(300):
            it = g.spawn_item()
            self.assertGreaterEqual(it.x, 0.15 * W)
            self.assertLessEqual(it.x, 0.85 * W)
            self.assertGreater(it.y, H)         
            self.assertLess(it.vy, 0)           
            self.assertIn(it.kind, (gl.APPLE, gl.STAR, gl.BOMB))

    def test_items_fall_off_and_removed(self):
        g = make_playing_game(seed=6)
        g.spawn_timer = 0
        blade = gl.Blade()
        for _ in range(600):                    
            g.update(1 / 30, blade)
        self.assertEqual(g.state, gl.PLAYING)
        self.assertEqual(g.hp, gl.MAX_HP)       
        self.assertLess(len(g.items), 60)       

    def test_simulation_does_not_crash(self):
        g = gl.SliceGame(W, H, rng=random.Random(7))
        g.start()
        rnd = random.Random(8)
        blade = gl.Blade()
        for i in range(3000):
            blade.update((rnd.uniform(0, W), rnd.uniform(0, H)), 1 / 30, i / 30)
            g.update(1 / 30, blade)
            g.pop_events()
            if g.state == gl.GAME_OVER:
                g.start()


if __name__ == "__main__":
    unittest.main()
