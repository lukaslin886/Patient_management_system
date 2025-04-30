import os
import shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS

def create_backup_directory():
    backup_dir = "backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir

def backup_database(db_path, backup_dir):
    backup_path = os.path.join(backup_dir, f"patient_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy(db_path, backup_path)
    return backup_path

def add_watermark(image_path, output_path, watermark_text):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 36)
    text_width, text_height = draw.textsize(watermark_text, font=font)
    margin = 10
    x = image.width - text_width - margin
    y = image.height - text_height - margin
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 128))
    image.save(output_path)

def get_exif_date(image_path):
    image = Image.open(image_path)
    exif_data = image._getexif()
    if exif_data:
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == 'DateTimeOriginal':
                return value
    return None
