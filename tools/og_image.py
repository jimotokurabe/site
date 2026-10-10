"""共有画像（LINE・X などでリンクを貼ったときに出る画像）を作る。

実行には日本語フォントのファイルが必要なので、ふだんの build では作り直さず、
できあがった assets/og-image.png をそのままコミットしておく。

    python3 tools/og_image.py --font /path/to/NotoSansJP-Bold.ttf
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'og-image.png'
W, H = 1200, 630
BG, INK, MUTED, LINK, LINE = '#0e171d', '#edf3f5', '#b5c7d0', '#9cd4e8', '#425b69'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--font', required=True, help='太字の日本語フォント（.ttf/.otf）')
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args()
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=LINK)
    big = ImageFont.truetype(a.font, 112)
    mid = ImageFont.truetype(a.font, 44)
    small = ImageFont.truetype(a.font, 30)
    x, y = 80, 150
    d.text((x, y), 'じもと', font=big, fill=INK)
    d.text((x + d.textlength('じもと', font=big), y), 'くらべ', font=big, fill=LINK)
    y += 160
    d.text((x, y), '免許返納の特典・バス・タクシーの支援を', font=mid, fill=INK)
    d.text((x, y + 66), '市町村ごとに、公式ページで確かめて比べる', font=mid, fill=INK)
    d.line([x, 520, W - 80, 520], fill=LINE, width=2)
    d.text((x, 545), '全国1,741市区町村  jimotokurabe.jp', font=small, fill=MUTED)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out, optimize=True)
    print('wrote', a.out, img.size)


if __name__ == '__main__':
    main()
