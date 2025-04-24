# PicCord

Discordにおいて画像の共有をより安全にするbot。

## 🔧 概要

PicCordは、Discordで画像を共有する際、閲覧者固有のタグを埋め込めるようにすることで
誰が取得した画像かがわかるようになるシステムです。

## 🧩 主な機能

- 投稿した画像に、閲覧者固有タグを埋め込む
- 元画像と比較することで"誰が取得した画像か"がわかる

## 🚀 セットアップ方法

```bash
git clone https://github.com/BoruChiso/PicCord.git
cd PicCord
# 仮想環境の作成など
pip install -r requirements.txt

# 次の環境変数を登録してください:
TOKEN: discordのbotトークン。
ID_ROOM_BOT: 投稿された画像をbotが保存するチャンネルのID。botのみ閲覧可能となるよう権限を設定してください。
ID_ROOM_VIEW: 投稿された画像が閲覧できるチャンネルのID。
ID_ROOM_PIC: 画像を投稿するためのチャンネルのID。

python main.py
```

