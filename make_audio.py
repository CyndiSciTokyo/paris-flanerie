#!/usr/bin/env python3
"""给 page.html 里所有会被朗读的法语生成录音，存到 audio/ 下。

用法:  .venv/bin/python make_audio.py          只补缺的
       .venv/bin/python make_audio.py --force  全部重录
文件名是文本的 FNV-1a 哈希，和 page.html 里的 akey() 保持一致。
文本列表靠 macOS 自带的 osascript 运行页面里的数据得到。
"""
import asyncio, json, pathlib, subprocess, sys, tempfile
import edge_tts

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'audio'
VOICES = {'m': 'fr-FR-HenriNeural', 'f': 'fr-FR-DeniseNeural', 'u': 'fr-FR-VivienneMultilingualNeural'}
RATE = '-8%'

COLLECT = r'''
const out=[];const add=(t,v)=>{if(t&&!out.some(o=>o.t===t))out.push({t:t,v:v})};
DATA.forEach(S=>{const g=S.voice||(/^Le /.test(S.who)?'m':'f');
  S.steps.forEach(p=>{if(p.t==='listen')add(p.fr,g);if(p.npc)add(p.npc[0],g)})});
DATA.forEach(S=>{add(S.frPlace,'u');
  S.steps.forEach(p=>{if(p.t==='choose'||p.t==='avis')p.opts.forEach(o=>add(o[0],'u'));if(p.t==='fill')add(p.full,'u');if(p.t==='build')add(p.tokens.join(' '),'u')});
  S.carnet.forEach(c=>add(c[0],'u'));S.vocab.forEach(v=>add(v[0],'u'));S.lesson.ex.forEach(v=>add(v[0],'u'))});
SCENES.forEach(sc=>sc.hots.forEach(o=>add(o[0],'u')));
add(INTRO_FR,'u');ROOM.forEach(r=>{add(r.fr,'u');add(r.up.fr,'u')});
return JSON.stringify(out);
'''

def akey(t):
    x = 2166136261
    for ch in t.encode('utf-16-le'), :
        for i in range(0, len(ch), 2):
            x = ((x ^ (ch[i] | ch[i + 1] << 8)) * 16777619) & 0xffffffff
    return '%08x' % x

def texts():
    src = (HERE / 'page.html').read_text(encoding='utf-8')
    data = src[src.index('const DATA=['):src.index('/* ---------- helpers ---------- */')]
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write('(function(){' + data + COLLECT + '})()')
    return json.loads(subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, check=True).stdout)

async def main():
    force = '--force' in sys.argv
    OUT.mkdir(exist_ok=True)
    items = texts()
    keep = set()
    for it in items:
        path = OUT / (akey(it['t']) + '.mp3')
        keep.add(path.name)
        if path.exists() and not force:
            continue
        await edge_tts.Communicate(it['t'].replace('—', '.').replace('…', ''), VOICES[it['v']], rate=RATE).save(str(path))
        print('+', path.name, it['v'], it['t'])
    for old in OUT.glob('*.mp3'):
        if old.name not in keep:
            old.unlink(); print('-', old.name)
    print(len(items), '条文本，audio/ 下', len(list(OUT.glob('*.mp3'))), '个文件')

asyncio.run(main())
