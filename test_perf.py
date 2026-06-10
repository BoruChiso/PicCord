"""
CPU処理ベンチマーク — Discord 依存なし。
画像処理パイプライン（myCrypter + image2file + GaussianBlur）の所要時間を計測する。

実行:
    python -m pytest test_perf.py -v -s
"""

import os
import time
from io import BytesIO

import imagehash
import pytest
from PIL import Image, ImageFilter

from myCrypter import myCrypter
from perf import StageTimer, TotalTimer

TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "test.png")
INTERNAL_ID = 42
USER_NAME = "benchmark_user"


@pytest.fixture(scope="module")
def test_image() -> Image.Image:
    im = Image.open(TEST_IMAGE_PATH).convert("RGBA")
    print(f"\n[INFO] test image size: {im.size}, mode: {im.mode}")
    return im


def _image2file_time(image: Image.Image) -> float:
    """PNG encode + imagehash の合計時間を ms で返す。"""
    t = time.perf_counter()
    buf = BytesIO()
    image.save(buf, format="png")
    buf.seek(0)
    imagehash.average_hash(image)
    return (time.perf_counter() - t) * 1000


def test_gaussianblur_full(test_image):
    """GaussianBlur(radius=100) フル解像度 — 現行実装。"""
    with StageTimer("bench/gaussianblur_r100_full"):
        _ = test_image.filter(ImageFilter.GaussianBlur(100))


def test_gaussianblur_downsample(test_image):
    """GaussianBlur 縮小→blur→拡大 — 最適化候補。"""
    intensity = 30
    minlength = 40
    w, h = test_image.size
    if w > h:
        sw = min(max(w // intensity, minlength), w)
        sh = max(h * sw // w, 1)
    else:
        sh = min(max(h // intensity, minlength), h)
        sw = max(w * sh // h, 1)

    with StageTimer("bench/gaussianblur_downsample"):
        small = test_image.resize((sw, sh))
        blurred_small = small.filter(ImageFilter.GaussianBlur(10))
        _ = blurred_small.resize((w, h), resample=Image.Resampling.NEAREST)


def test_encrypt_pipeline(test_image):
    """myCrypter フルパイプライン（encryptByID + encryptByLabel + encryptByTime + executeEncryption）。"""
    total = TotalTimer("bench/encrypt_pipeline")
    total.start()

    c = myCrypter(test_image)
    c.setChannel([True, False, False, True]).encryptByID(INTERNAL_ID)
    c.setChannel([False, False, True, True]).encryptByLabel(USER_NAME).encryptByTime()
    result = c.executeEncryption()

    total.stop()
    assert result.size == test_image.size


def test_png_encode(test_image):
    """PNG encode + imagehash の時間。"""
    with StageTimer("bench/png_encode_and_hash"):
        ms = _image2file_time(test_image)
    print(f"  → png+hash total: {ms:.1f}ms")


def test_rgba_convert():
    """JPEG → RGBA 変換コスト。test.png が既に RGBA の場合は参考値。"""
    im_rgb = Image.open(TEST_IMAGE_PATH).convert("RGB")
    with StageTimer("bench/convert_rgb_to_rgba"):
        _ = im_rgb.convert("RGBA")


def test_full_flow(test_image):
    """投稿時フロー全体（GaussianBlur + PNG encode）と閲覧時フロー全体（encrypt + PNG encode）を通し計測。"""
    print("\n--- 投稿時フロー ---")
    total_upload = TotalTimer("bench/upload_flow")
    total_upload.start()
    with StageTimer("bench/upload/gaussianblur"):
        blur = test_image.filter(ImageFilter.GaussianBlur(100))
    with StageTimer("bench/upload/png_encode_blur"):
        buf = BytesIO()
        blur.save(buf, format="png")
    total_upload.stop()

    print("--- 閲覧時フロー（キャッシュなし）---")
    total_view = TotalTimer("bench/view_flow")
    total_view.start()
    c = myCrypter(test_image)
    c.setChannel([True, False, False, True]).encryptByID(INTERNAL_ID)
    c.setChannel([False, False, True, True]).encryptByLabel(USER_NAME).encryptByTime()
    with StageTimer("bench/view/executeEncryption"):
        encrypted = c.executeEncryption()
    with StageTimer("bench/view/png_encode_encrypted"):
        buf2 = BytesIO()
        encrypted.save(buf2, format="png")
    total_view.stop()
