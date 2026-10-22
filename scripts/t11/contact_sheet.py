"""T11: フォルダ内の face_az*.png を方位順に並べた確認用コンタクトシートを作る。python contact_sheet.py DIR OUT.jpg [cols]"""
import sys, glob, re
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 9
fs = sorted(glob.glob(d + "/face_az*.png"), key=lambda f: int(re.search(r"az([+-]\d+)", f).group(1)))
tw, th = 230, 288; rows = (len(fs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), "white"); dr = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = Image.open(f).convert("RGB").resize((tw, th - 16), Image.LANCZOS); x, y = (i % cols) * tw, (i // cols) * th
    sheet.paste(im, (x, y + 16)); dr.text((x + 4, y + 2), re.search(r"az([+-]\d+)", f).group(1), fill="black")
sheet.save(out, quality=88)
