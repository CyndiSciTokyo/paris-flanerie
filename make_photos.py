#!/usr/bin/env python3
"""给每一站生成一张拍立得照片，存到 photos/<站号>.jpg。

密钥只从本机读取，不会进入网页或仓库：
  先看环境变量 OPENAI_API_KEY，没有就读 ~/.openai_api_key 这个文件。

用法:  python3 make_photos.py            只补缺的
       python3 make_photos.py --only 3   只重做第 3 站
       python3 make_photos.py --force    全部重做
可选环境变量 OPENAI_IMAGE_MODEL（默认 gpt-image-1）。
"""
import base64, json, os, pathlib, subprocess, sys, tempfile, time, urllib.error, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'photos'
MODEL = os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1')

STYLE = ('A vintage Polaroid instant photograph, the square image only (no white border). '
         'Warm faded colours, soft on-camera flash, light film grain, slight vignette, Paris. '
         'No text, no letters, no logos, no watermark. No recognisable faces: if a person appears, '
         'show only their hands or a figure seen from behind. Scene: ')

# one scene per stop, in the same order as DATA in page.html
SCENES = [
    "hands holding an old worn copy of a 19th-century poetry book in front of a dark green bouquiniste book box on the stone wall of the Seine, the river and an old stone bridge behind, spring morning",
    "a café crème in a white cup on a small round marble table, an open notebook and a fountain pen, inside a classic Paris café with mirrors and red banquettes, pale winter light through the window",
    "the view through the giant transparent clock face of the Musée d'Orsay, looking across the Seine toward the hill of Montmartre, the clock's black numerals and hands in silhouette",
    "the red-brick arcades and square of the Place des Vosges with trees and a fountain, an old handwritten manuscript page and a quill pen on a stone bench in the foreground",
    "an easel on the Place du Tertre in Montmartre holding a small fresh oil painting of the white Sacré-Cœur basilica, a painter's palette and brushes, café umbrellas behind",
    "a small madeleine cake and a single red rose laid on a plain black marble tombstone in Père-Lachaise cemetery, autumn leaves, cobblestone path, no inscriptions",
    "a wooden toy sailboat with a striped sail on the large round pond of the Jardin du Luxembourg, green metal chairs around the pond, the palace in the background, late afternoon sun",
    "a worn brown leather jacket on a rack in a cosy vintage clothing shop in the Marais, an old gilded mirror and a felt hat, the narrow old street seen through the shop window",
    "a round table in an Art Deco Paris brasserie with painted columns, a tobacco pipe, round spectacles and an open notebook on the table, warm evening light",
    "a writer's study with tall bookshelves, a desk covered with handwritten manuscript pages, a red turban-style headscarf draped over a chair, a window looking out on cemetery trees",
    "a plain pale stone tombstone covered with paper metro tickets, a red rose and faint lipstick marks, Montparnasse cemetery, soft overcast light, no readable inscriptions",
    "dusk on the Canal Saint-Martin, an arched iron footbridge reflected in the water, a hand holding a small paper cinema ticket in the foreground",
    "a vinyl record spinning on a turntable in a small record shop, colourful record sleeves in wooden crates, the canal visible through the window",
    "looking up from a red velvet seat at the huge crystal chandelier and the colourful painted ceiling of the Palais Garnier opera house, gold balconies around",
    "a picnic on a park bench: a baguette, a wedge of cheese, a punnet of strawberries and apples in a paper bag, outdoor market stalls with striped awnings in the background",
    "a bistro lunch on a red-and-white checked tablecloth: French onion soup with a melted cheese crust, steak-frites, a slice of apple tart and a carafe of water, a chalkboard menu on the wall behind",
]


def api_key():
    k = os.environ.get('OPENAI_API_KEY', '').strip()
    f = pathlib.Path.home() / '.openai_api_key'
    if not k and f.exists():
        k = f.read_text().strip()
    if not k:
        sys.exit('没有找到密钥：请设置 OPENAI_API_KEY，或把密钥存进 ~/.openai_api_key')
    return k


def generate(prompt, key):
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'quality': 'medium', 'n': 1}).encode()
    req = urllib.request.Request('https://api.openai.com/v1/images/generations', data=body,
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return base64.b64decode(json.load(r)['data'][0]['b64_json'])
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:300]
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(20 * (attempt + 1)); continue
            sys.exit(f'OpenAI 返回错误 {e.code}: {msg}')


def main():
    force = '--force' in sys.argv
    only = int(sys.argv[sys.argv.index('--only') + 1]) if '--only' in sys.argv else None
    OUT.mkdir(exist_ok=True)
    key = api_key()
    for i, scene in enumerate(SCENES, start=1):
        out = OUT / f'{i}.jpg'
        if only and i != only:
            continue
        if out.exists() and not force and not only:
            continue
        print(f'第 {i} 站 …', flush=True)
        png = generate(STYLE + scene, key)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png)
        # shrink to a light web image with macOS's built-in sips
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '78', '-Z', '640', f.name, '--out', str(out)],
                       check=True, capture_output=True)
        os.unlink(f.name)
        print(f'  已存 {out.name}（{out.stat().st_size // 1024} KB）')
    print('完成。photos/ 下共', len(list(OUT.glob('*.jpg'))), '张')


if __name__ == '__main__':
    main()
