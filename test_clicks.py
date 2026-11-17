import unittest
from types import SimpleNamespace

import numpy as np

from gaze import WinkController, eye_openness


class WinkTests(unittest.TestCase):
    def setUp(self):
        self.controller = WinkController()
        self.controller.calibrate([[0.3, 0.3]] * 20)
        self.now = 0
        self.events = []
        self.hold([0.3, 0.3], 6)

    def hold(self, values, frames, enabled=True):
        for _ in range(frames):
            self.now += 0.05
            event = self.controller.update(values, self.now, enabled)
            if event:
                self.events.append(event)

    def test_left_wink_clicks_once_on_release(self):
        self.hold([0.08, 0.3], 13)
        self.assertTrue(self.controller.frozen)
        self.assertEqual(self.events, [])
        self.hold([0.3, 0.3], 30)
        self.assertEqual(self.events, ['left'])

    def test_right_wink(self):
        self.hold([0.3, 0.08], 13)
        self.hold([0.3, 0.3], 1)
        self.assertEqual(self.events, ['right'])
        self.assertTrue(self.controller.frozen)

    def test_short_wink_is_ignored(self):
        self.hold([0.08, 0.3], 3)
        self.hold([0.3, 0.3], 10)
        self.assertEqual(self.events, [])

    def test_bilateral_blink_and_asymmetric_reopening_are_ignored(self):
        self.hold([0.08, 0.3], 2)
        self.hold([0.08, 0.08], 12)
        self.hold([0.3, 0.08], 12)
        self.hold([0.3, 0.3], 5)
        self.assertEqual(self.events, [])

    def test_long_closure_is_ignored(self):
        self.hold([0.08, 0.3], 40)
        self.hold([0.3, 0.3], 5)
        self.assertEqual(self.events, [])

    def test_loss_pause_and_frame_gap_cancel_pending_click(self):
        for reason in ('lost', 'paused', 'gap'):
            with self.subTest(reason=reason):
                self.setUp()
                self.hold([0.08, 0.3], 13)
                if reason == 'lost':
                    self.hold(None, 1)
                elif reason == 'paused':
                    self.hold([0.08, 0.3], 1, enabled=False)
                else:
                    self.now += 0.4
                self.hold([0.3, 0.3], 5)
                self.assertEqual(self.events, [])

    def test_must_open_both_eyes_before_starting(self):
        self.controller.reset()
        self.hold([0.08, 0.3], 13)
        self.hold([0.3, 0.3], 5)
        self.assertEqual(self.events, [])

    def test_cooldown_prevents_second_click(self):
        self.hold([0.08, 0.3], 13)
        self.hold([0.3, 0.3], 1)
        self.hold([0.3, 0.08], 11)
        self.hold([0.3, 0.3], 5)
        self.assertEqual(self.events, ['left'])

    def test_openness_sorted_by_mirrored_screen_position(self):
        points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(478)]
        for left, right, top, bottom, iris, x, gap in [
            (33, 133, 159, 145, 468, 0.7, 0.06),
            (362, 263, 386, 374, 473, 0.2, 0.02),
        ]:
            for index, px, py in [(left, x, 0.5), (right, x + 0.2, 0.5),
                                  (top, x + 0.1, 0.5 - gap / 2),
                                  (bottom, x + 0.1, 0.5 + gap / 2),
                                  (iris, x + 0.1, 0.5)]:
                points[index] = SimpleNamespace(x=px, y=py)
        np.testing.assert_allclose(eye_openness(points, 1000, 1000), [0.1, 0.3])

    def test_invalid_calibration(self):
        for samples in ([], [[0.3, 0.3]] * 2, [[0.05, 0.3]] * 20):
            with self.assertRaises(ValueError):
                self.controller.calibrate(samples)


if __name__ == '__main__':
    unittest.main()
