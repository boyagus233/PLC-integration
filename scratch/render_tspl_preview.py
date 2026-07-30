import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def render_masterbox():
    width, height = 560, 400
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font_header = ImageFont.truetype("arialbd.ttf", 22)
        font_code = ImageFont.truetype("arialbd.ttf", 15)
        font_text = ImageFont.truetype("arial.ttf", 12)
    except:
        font_header = font_code = font_text = ImageFont.load_default()

    code = "YBID.MB.250908.08.000001"
    part_code = "M221SDCAC20"
    batt_type = "B.CH-YTZ5S (Wet-CF) YU-5"
    quantity = "10"
    weight = "15.44"
    date_str = "25-Sep-2025"
    line_no = "14"

    # Shifted down by 50 dots (approx 6.25mm)
    draw.text((20, 55), "PT. YUASA BATTERY INDONESIA", fill=(0, 0, 0), font=font_header)
    draw.line([(20, 83), (440, 83)], fill=(0, 0, 0), width=3)
    
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((130, 130))
    img.paste(qr_img, (20, 115))
    
    draw.text((180, 110), code, fill=(0, 0, 0), font=font_code)
    draw.text((180, 150), f"Part Code  : {part_code}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 190), f"TYPE       : {batt_type}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 230), f"Quantity   : {quantity} Pcs    BERAT : {weight} KG", fill=(0, 0, 0), font=font_text)
    draw.text((180, 270), f"Prd/Shift/Mc : {date_str}/I/{line_no}", fill=(0, 0, 0), font=font_text)

    img.save("scratch/masterbox_preview.png")

def render_pallet():
    width, height = 560, 400
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font_header = ImageFont.truetype("arialbd.ttf", 22)
        font_code = ImageFont.truetype("arial.ttf", 12)
        font_text = ImageFont.truetype("arial.ttf", 12)
    except:
        font_header = font_code = font_text = ImageFont.load_default()

    code = "YBID.PLT.250908.000001"
    part_code = "M221SDCAC20"
    batt_type = "B.CH-YTZ5S (Wet-CF) YU-5"
    quantity = "640 PCS - 64 Pack"
    date_str = "25-Sep-2025"
    line_no = "14"

    # Shifted down by 50 dots
    draw.text((20, 55), "PT. YUASA BATTERY INDONESIA", fill=(0, 0, 0), font=font_header)
    draw.line([(20, 83), (440, 83)], fill=(0, 0, 0), width=3)
    
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((130, 130))
    img.paste(qr_img, (20, 115))
    
    draw.text((180, 110), f"Group Code : {code}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 143), f"Order No.  : -", fill=(0, 0, 0), font=font_text)
    draw.text((180, 176), f"Customer   : AFM (PT. SANTI YOGA)", fill=(0, 0, 0), font=font_text)
    draw.text((180, 209), f"Part Code  : {part_code}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 242), f"Batt. Type : {batt_type}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 275), f"Quantity   : {quantity}", fill=(0, 0, 0), font=font_text)
    draw.text((180, 308), f"Prod. /Shift/Mc : {date_str}/I/{line_no}", fill=(0, 0, 0), font=font_text)

    img.save("scratch/pallet_preview.png")

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    render_masterbox()
    render_pallet()
