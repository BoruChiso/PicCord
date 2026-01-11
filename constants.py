"""
PicCord定数定義ファイル

このファイルには、プロジェクト全体で使用される定数が定義されています。
"""

# ===============================
# 暗号化関連定数
# ===============================

# ビットマスクのグリッドサイズ
MASKBIT_ROW = 4
MASKBIT_COLUMN = 5

# ビット長
MASKBIT_LENGTH_NUM = 16
MASKBIT_LENGTH_CHECKSUM = 4

# ID最大値 (2^16 = 65536)
ID_MAX = 2**MASKBIT_LENGTH_NUM

# マスク色設定
MASK_BASE = 0
MASK_COLOR = 1  # 透かしの強度（1 = ほぼ不可視）
TEXT_COLOR = 64  # タイムスタンプのテキスト色

# ===============================
# Discord UI関連定数
# ===============================

# インタラクションID
INTER_ID_BUTTONCLICK_IMAGEVIEW = 2
INTER_ID_BUTTONCLICK_IMAGEREMOVE = 3
INTER_ID_BUTTONCLICK_IMAGEREMOVEYES = 4
INTER_ID_BUTTONCLICK_IMAGEREMOVENO = 5

# 絵文字定数
EMOJI_BUTTON_PREVIOUS = "\N{BLACK LEFT-POINTING TRIANGLE}"
EMOJI_BUTTON_NEXT = "\N{BLACK RIGHT-POINTING TRIANGLE}"
EMOJI_EYES = "\N{EYES}"
EMOJI_TRASHCAN = "\N{WASTEBASKET}"

# ===============================
# JSONキー定数
# ===============================

# カスタムIDで使用されるJSONキー
KEY_ID = "id"
KEY_THREAD_ID = "thread_id"
KEY_AUTHOR_ID = "author_id"
