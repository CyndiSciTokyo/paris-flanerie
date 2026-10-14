#!/usr/bin/env python3
"""给每一站生成一张拍立得照片，存到 photos/<站号>.jpg。

照片里是同一位卡通女主角。先生成她的人物设定图 photos/ref/heroine.png，
之后每一站都把这张图交给模型做参考，让她在每张照片里长得一样。
拍立得相纸的边框由网页加上，图片本身是方形画面。

密钥只从本机读取，不会进入网页或仓库：
  先看环境变量 OPENAI_API_KEY，没有就读 ~/.openai_api_key 这个文件。

用法:  python3 make_photos.py --heroine    生成（或重做）女主角设定图
       python3 make_photos.py              只补缺的照片
       python3 make_photos.py --only 3     只重做第 3 站
       python3 make_photos.py --force      全部重做
       python3 make_photos.py --sample 3   只试做第 3 站，存成 photos/sample-3.jpg，网页不会用它
可选环境变量 OPENAI_IMAGE_MODEL（默认 gpt-image-1）。
"""
import base64, json, os, pathlib, subprocess, sys, tempfile, time, urllib.error, urllib.request, uuid

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'photos'
REF = OUT / 'ref' / 'heroine.png'
# the player's own portrait, kept outside the repository so it is never published
ME = pathlib.Path.home() / '.config' / 'paris-flanerie' / 'me.jpg'
MODEL = os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1')

STYLE = ('A stylish cartoon illustration that looks like a vintage Fujifilm instant photo. '
         'Flat shapes, clean ink outlines and a light hand-drawn texture, like a modern European picture book or a ligne claire comic. '
         'Colours graded like old Fuji film: clearly teal-green shadows, creamy warm highlights, soft low contrast, a faint magenta cast, '
         'fine grain and a gentle light leak in one corner. No text, letters, logos or watermark. '
         'The only person shown is the fictional heroine; no real or famous people. ')

HEROINE = ('a young woman: short black hair in a chin-length French bob with soft loose curls, '
           'small gold hoop earrings; she wears an oversized cream trench coat '
           'over a navy-and-white striped Breton top, high-waisted black wide-leg trousers, a thin red silk scarf at the neck and black loafers')

KEEP = ('The heroine is the young woman in the reference image: keep her face and her short black bob exactly the same. '
        'Ignore the clothes in the reference image and dress her as described here. ')

# what she wears at each stop, same order as SCENES: a different Paris look every time
OUTFITS = [
    "a cream trench coat over a navy-and-white striped Breton top, a thin red silk scarf and black wide-leg trousers",
    "a camel wool coat over a black turtleneck and grey wool trousers",
    "a navy double-breasted blazer, a white shirt, straight light-blue jeans and a small black leather shoulder bag",
    "a pale blue linen shirt dress with a thin brown belt and white canvas sneakers",
    "denim dungarees over a white T-shirt, a red beret and a few paint smudges",
    "a long dark green wool coat, a cream knitted scarf and black ankle boots",
    "a soft yellow-and-white gingham summer dress and white canvas sneakers",
    "a white T-shirt and high-waisted vintage jeans",
    "a black velvet dress with a small white collar and black Mary-Jane shoes",
    "a cream cable-knit sweater and brown corduroy trousers",
    "a grey wool coat, a black turtleneck and a black beret",
    "an oversized denim jacket over a striped T-shirt, a black mini skirt and black tights",
    "a burgundy knitted cardigan over a white T-shirt and flared jeans",
    "an elegant emerald-green silk evening dress",
    "a white cotton blouse, a flowing midi skirt with a small floral print and a straw basket bag",
    "a cherry-red knitted polo top and black cigarette trousers",
]

# one scene per stop, in the same order as DATA in page.html
SCENES = [
    "At a dark green bouquiniste book box on the stone wall of the Seine, she leafs through an old worn 19th-century poetry book; the river and an old stone bridge behind, spring morning.",
    "Inside a classic Paris café with mirrors and red banquettes she sits at a small round marble table writing in a notebook, a café crème beside her, pale winter light through the window.",
    "Seen from behind, she stands in front of the giant transparent clock face of the Musée d'Orsay, looking across the Seine toward the hill of Montmartre; the clock's black numerals and hands in silhouette.",
    "Under the red-brick arcades of the Place des Vosges she sits on a stone bench reading an old handwritten manuscript, a quill pen beside her, trees and a fountain in the square.",
    "On the Place du Tertre in Montmartre she paints at an easel, a small fresh oil painting of the white Sacré-Cœur basilica on it, palette in hand, café umbrellas behind.",
    "In Père-Lachaise cemetery she gently lays a small madeleine cake and a red rose on a plain black marble tombstone with no inscription, autumn leaves on the cobblestone path.",
    "By the large round pond of the Jardin du Luxembourg she pushes a wooden toy sailboat with a striped sail using a long stick, green metal chairs around the pond, the palace behind, late afternoon sun.",
    "In a cosy vintage clothing shop in the Marais she tries on a worn brown leather jacket in front of an old gilded mirror, a felt hat on a stand, the narrow old street through the window.",
    "In an Art Deco Paris brasserie with painted columns she sits at a round table thinking, chin on hand; across from her an empty chair, and on the table a tobacco pipe, round spectacles and an open notebook, warm evening light.",
    "In a writer's study full of tall bookshelves and photographs she sits on a yellow sofa reading handwritten manuscript pages; a red turban-style headscarf lies on the armrest; a window shows cemetery trees.",
    "In Montparnasse cemetery she places a paper metro ticket on a plain pale stone tombstone already covered with metro tickets and a red rose, no readable inscriptions, soft overcast light.",
    "At dusk she stands on an arched iron footbridge over the Canal Saint-Martin holding a small plain cinema ticket with nothing written on it, the bridge reflected in the water, street lamps coming on.",
    "In a small record shop she listens on big headphones while a vinyl record spins on a turntable, colourful record sleeves in wooden crates, the canal visible through the window.",
    "Seen from behind and slightly to the side, she sits in a red velvet seat looking up at the huge crystal chandelier and the colourful painted ceiling of the Palais Garnier opera house, gold balconies around.",
    "She has a picnic on a park bench: a baguette, a wedge of cheese, strawberries and apples in a paper bag beside her; outdoor market stalls with striped awnings in the background.",
    "In a Paris bistro she raises a glass over a lunch on a red-and-white checked tablecloth: French onion soup with a melted cheese crust, steak-frites and a slice of apple tart; a dark chalkboard on the wall behind with only simple chalk doodles of a bowl and a fork, absolutely no words or letters.",
]


assert len(OUTFITS) == len(SCENES)


def api_key():
    k = os.environ.get('OPENAI_API_KEY', '').strip()
    f = pathlib.Path.home() / '.openai_api_key'
    if not k and f.exists():
        k = f.read_text().strip()
    if not k:
        sys.exit('没有找到密钥：请设置 OPENAI_API_KEY，或把密钥存进 ~/.openai_api_key')
    return k


def call(url, key, body, ctype):
    req = urllib.request.Request(url, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': ctype})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=400) as r:
                res = json.load(r)
                print('  用量:', json.dumps(res.get('usage') or {}, ensure_ascii=False))
                return base64.b64decode(res['data'][0]['b64_json'])
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:400]
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(20 * (attempt + 1)); continue
            sys.exit(f'OpenAI 返回错误 {e.code}: {msg}')


def generate(prompt, key, size='1024x1024'):
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': 'medium', 'n': 1}).encode()
    return call('https://api.openai.com/v1/images/generations', key, body, 'application/json')


def edit(prompt, key, ref, size='1024x1024'):
    """generate with a reference image (multipart form)"""
    mime = 'png' if ref.suffix == '.png' else 'jpeg'
    b = uuid.uuid4().hex
    fields = {'model': MODEL, 'prompt': prompt, 'size': size, 'quality': 'medium', 'input_fidelity': 'high', 'n': '1'}
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="image[]"; filename="{ref.name}"\r\nContent-Type: image/{mime}\r\n\r\n'.encode()
                 + ref.read_bytes() + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    return call('https://api.openai.com/v1/images/edits', key, b''.join(parts), f'multipart/form-data; boundary={b}')


def save_jpg(png, out, size=640):
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(png)
    # shrink to a light web image with macOS's built-in sips
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80', '-Z', str(size), f.name, '--out', str(out)],
                   check=True, capture_output=True)
    os.unlink(f.name)
    print(f'  已存 {out.relative_to(HERE)}（{out.stat().st_size // 1024} KB）')


def main():
    arg = lambda name: int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else None
    force, only, sample = '--force' in sys.argv, arg('--only'), arg('--sample')
    key = api_key()
    if '--heroine' in sys.argv or not REF.exists():
        REF.parent.mkdir(parents=True, exist_ok=True)
        print('女主角设定图 …', flush=True)
        sheet = ('Character reference sheet on a plain warm cream background: a full-body front view and a '
                 'three-quarter view of the same character, ' + HEROINE + '.')
        if ME.exists():   # design the heroine after the player's own portrait
            REF.write_bytes(edit('Turn the woman in this portrait photo into a cartoon character, keeping her recognisable: '
                                 'her face shape, eyes, eyebrows, nose, gentle closed-mouth smile and skin tone. '
                                 + STYLE.replace('The only person shown is the fictional heroine; no real or famous people. ', '') + sheet, key, ME, '1536x1024'))
        else:
            REF.write_bytes(generate(STYLE + sheet, key, '1536x1024'))
        save_jpg(REF.read_bytes(), REF.with_suffix('.jpg'), 900)
        if '--heroine' in sys.argv and not (only or sample):
            return
    for i, scene in enumerate(SCENES, start=1):
        target = sample or only
        if target and i != target:
            continue
        out = OUT / (f'sample-{i}.jpg' if sample else f'{i}.jpg')
        if out.exists() and not force and not target:
            continue
        print(f'第 {i} 站 …', flush=True)
        save_jpg(edit(KEEP + 'She wears ' + OUTFITS[i - 1] + '. ' + STYLE + 'Square image, no border. Scene: ' + scene, key, REF), out)
    print('完成。')


if __name__ == '__main__':
    main()
