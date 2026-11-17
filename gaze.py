import numpy as np


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
