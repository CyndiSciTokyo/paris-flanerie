# 巴黎文艺漫步 · Flânerie à Paris

在巴黎七个文学艺术地点完成小任务，边听发音边学法语日常用语和语法的小游戏。

## 点这里开始玩

**https://cyndiscitokyo.github.io/paris-flanerie/**

不用登录，电脑和手机都能打开。

## 怎么玩

用 Chrome、Safari 或 Edge 打开上面的地址（或本地的 `index.html`）。每句法语旁边有喇叭按钮，播放的是提前录好的神经语音（`audio/` 下的 mp3）；录音加载不出来时才改用设备自带的法语语音。

## 路线

| 站 | 地点 | 任务 | 语法 |
|---|---|---|---|
| 1 | 塞纳河旧书摊 | 买《恶之花》 | un / une |
| 2 | 花神咖啡馆 | 点咖啡、结账 | je voudrais，être |
| 3 | 奥赛博物馆 | 买票、找印象派 | le / la / les，où est / où sont |
| 4 | 孚日广场雨果故居 | 问路 | au / à la |
| 5 | 蒙马特画家广场 | 夸一幅画 | 形容词跟名词变 |
| 6 | 拉雪兹神父公墓 | 找普鲁斯特的墓 | 过去的事 |
| 7 | 卢森堡公园 | 聊天气和今晚的打算 | 马上要做的事 |

## 文件

- `page.html`：游戏本体，情节、插图和程序都在这一个文件里。改内容只改它。
- `make_audio.py`：给 `page.html` 里所有法语生成录音。改了法语内容后运行 `.venv/bin/python make_audio.py`（首次需要 `python3 -m venv .venv && .venv/bin/pip install edge-tts`）。
- `audio/`：录音文件，文件名是文本的哈希。
- `build.py`：运行 `python3 build.py`，把 `page.html` 包成 `index.html`。
- `index.html`：生成出来的成品，可以直接打开。
