#!/usr/bin/env python3
"""把 page.html(游戏本体)包成可以直接用浏览器打开的 index.html。"""
import pathlib
here = pathlib.Path(__file__).resolve().parent
head = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n')
(here / 'index.html').write_text(head + (here / 'page.html').read_text(encoding='utf-8') + '\n</body></html>\n', encoding='utf-8')
print('index.html 已生成')
