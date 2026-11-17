import numpy as np


def eye_openness(landmarks, width, height):
    points = np.array([(p.x * width, p.y * height) for p in landmarks])
    eyes = []
    for left, right, top, bottom, iris in [(33, 133, 159, 145, 468),
                                          (362, 263, 386, 374, 473)]:
        size = np.linalg.norm(points[right] - points[left])
        if size < 4:
            return None
        eyes.append((points[iris, 0], np.linalg.norm(points[top] - points[bottom]) / size))
    values = np.array([value for _, value in sorted(eyes)])
    return values if np.isfinite(values).all() else None


class WinkController:
    def __init__(self):
        self.baseline = None
        self.reset()

    def reset(self):
        self.candidate = None
        self.started = None
        self.open_since = None
        self.armed = False
        self.last_time = None
        self.cooldown_until = 0
        self.frozen = True

    def calibrate(self, samples):
        values = np.asarray(samples, dtype=float)
        if values.shape != (len(values), 2) or len(values) < 15 or not np.isfinite(values).all():
            raise ValueError('Poucas amostras dos olhos. Repita a calibracao.')
        baseline = np.median(values, axis=0)
        if np.any(baseline < 0.12):
            raise ValueError('Calibre com os dois olhos abertos.')
        self.baseline = baseline
        self.reset()

    def update(self, openness, now, enabled=True):
        if not enabled or openness is None or self.baseline is None:
            self.reset()
            return None
        if self.last_time is not None and (now - self.last_time > 0.25 or now < self.last_time):
            self.reset()
        self.last_time = now
        ratio = np.asarray(openness) / self.baseline
        if not np.isfinite(ratio).all():
            self.reset()
            return None
        closed = ratio <= 0.55
        opened = ratio >= 0.75
        both_open = bool(np.all(opened))
        self.frozen = not both_open or now < self.cooldown_until
        if now < self.cooldown_until:
            return None
        if both_open:
            button = None
            if self.candidate is not None and 0.5 <= now - self.started <= 1.5:
                button = self.candidate
                self.cooldown_until = now + 0.7
                self.frozen = True
            self.candidate = None
            self.started = None
            if self.open_since is None:
                self.open_since = now
            self.armed = button is None and now - self.open_since >= 0.15
            return button
        self.open_since = None
        if np.all(closed):
            self.candidate = None
            self.armed = False
        elif self.candidate is not None:
            opposite = 1 if self.candidate == 'left' else 0
            if closed[opposite] or now - self.started > 1.5:
                self.candidate = None
                self.armed = False
        elif self.armed:
            if closed[0] and opened[1]:
                self.candidate, self.started, self.armed = 'left', now, False
            elif closed[1] and opened[0]:
                self.candidate, self.started, self.armed = 'right', now, False
        return None


def eye_position(landmarks, width, height):
    points = np.array([(p.x * width, p.y * height) for p in landmarks])
    eyes = []
    for left, right, top, bottom, iris in [(33, 133, 159, 145, 468),
                                          (362, 263, 386, 374, 473)]:
        axis = points[right] - points[left]
        if axis[0] < 0:
            axis = -axis
        size = np.linalg.norm(axis)
        if size < 4 or np.linalg.norm(points[top] - points[bottom]) / size < 0.12:
            return None
        horizontal = axis / size
        vertical = np.array([-horizontal[1], horizontal[0]])
        center = (points[left] + points[right]) / 2
        eyes.append([(points[iris] - center) @ horizontal / size,
                     (points[iris] - center) @ vertical / size])
    result = np.mean(eyes, axis=0)
    return result if np.isfinite(result).all() else None


class EyeController:
    def __init__(self, sensitivity=1.0):
        self.sensitivity = sensitivity
        self.center = None
        self.filtered = None

    def calibrate(self, samples):
        values = np.asarray(samples)
        if len(values) < 15 or not np.isfinite(values).all():
            raise ValueError('Poucas amostras. Olhe ao centro e tente novamente.')
        center = np.median(values, axis=0)
        noise = np.median(np.abs(values - center), axis=0) * 1.4826
        if np.any(noise > [0.025, 0.018]):
            raise ValueError('Olhar instavel. Mantenha os olhos no centro e repita.')
        self.center = center
        self.deadzone = np.maximum([0.012, 0.006], noise * 2.5)
        self.filtered = None

    def velocity(self, gaze, dt):
        if gaze is None or self.center is None:
            self.filtered = None
            return np.zeros(2)
        gaze = np.asarray(gaze)
        if self.filtered is None:
            self.filtered = gaze.copy()
        self.filtered += (1 - np.exp(-dt / 0.08)) * (gaze - self.filtered)
        offset = self.filtered - self.center
        amount = np.maximum(np.abs(offset) - self.deadzone, 0)
        amount = np.clip(amount * self.sensitivity / [0.10, 0.035], 0, 1)
        return np.sign(offset) * amount ** 1.4 * 1100
