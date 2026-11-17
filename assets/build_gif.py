from pathlib import Path

from PIL import Image


folder = Path(__file__).resolve().parent
sheet = Image.open(folder / 'visionflow-frames.png').convert('RGB')
width, height = sheet.size
if width % 2 or height % 2:
    raise ValueError('A imagem deve conter uma grade 2x2 de quadros iguais.')

palette = sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
frames = []
for row in range(2):
    for column in range(2):
        bounds = (column * width // 2, row * height // 2,
                  (column + 1) * width // 2, (row + 1) * height // 2)
        frame = sheet.crop(bounds).quantize(palette=palette, dither=Image.Dither.NONE)
        frames.append(frame)

sequence = [frames[i] for i in (0, 1, 2, 1, 0, 3)]
output = folder / 'visionflow.gif'
sequence[0].save(output, save_all=True, append_images=sequence[1:],
                 duration=200, loop=0, optimize=False, disposal=2)

with Image.open(output) as animation:
    assert animation.n_frames == len(sequence)
    assert animation.info['loop'] == 0
    for index in range(animation.n_frames):
        animation.seek(index)
        animation.load()
    print(f'{output.name}: {animation.size}, {animation.n_frames} quadros, '
          f'{output.stat().st_size / 1024:.0f} KB')
