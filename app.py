from flask import Flask, request, jsonify
import base64, math, random
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image
import piexif

app = Flask(__name__)

def decimal_to_exif_gps(value):
    v = abs(float(value))
    deg = int(v)
    minutes = int((v - deg) * 60)
    seconds = (v - deg - minutes / 60) * 3600
    return ((deg, 1), (minutes, 1), (int(seconds * 100), 100))

def math_cos_deg(deg):
    return math.cos(math.radians(deg))

def random_gps(lat0, lon0, meters=2):
    r = math.sqrt(random.random()) * meters
    theta = random.uniform(0, 2 * math.pi)
    dx = r * math.cos(theta)
    dy = r * math.sin(theta)
    dlat = dy / 111320.0
    dlon = dx / (111320.0 * math_cos_deg(lat0))
    return lat0 + dlat, lon0 + dlon

def fmt_exif_time(dt):
    return dt.strftime("%Y:%m:%d %H:%M:%S")

def gps_time_tuple(dt):
    return ((dt.hour, 1), (dt.minute, 1), (dt.second, 1))

@app.route('/procesar', methods=['POST'])
def procesar():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON inválido"}), 400

    image_b64 = data.get("image_base64")
    lat = data.get("latitude")
    lon = data.get("longitude")
    if not image_b64 or lat is None or lon is None:
        return jsonify({"error": "Faltan campos"}), 400

    if image_b64.startswith("data:image"):
        image_b64 = image_b64.split(",", 1)[1]

    img = Image.open(BytesIO(base64.b64decode(image_b64)))
    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Hora local España (+01:00)
    offset = timedelta(hours=1)
    now_local = datetime.now(timezone(offset))
    now_utc = now_local.astimezone(timezone.utc)
    subsec = int(now_local.microsecond / 1000)
    offset_str = "+01:00"

    lat_rand, lon_rand = random_gps(float(lat), float(lon), meters=2)

    exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif["0th"][piexif.ImageIFD.Make] = "samsung"
    exif["0th"][piexif.ImageIFD.Model] = "Galaxy A54 5G"
    exif["0th"][piexif.ImageIFD.Software] = "A546BXXSCCYD1"
    exif["0th"][piexif.ImageIFD.DateTime] = fmt_exif_time(now_local)
    exif["0th"][piexif.ImageIFD.ImageDescription] = "Procesada: metadatos generados"

    exif["Exif"][piexif.ExifIFD.ExposureTime] = (1, 221)
    exif["Exif"][piexif.ExifIFD.FNumber] = (18, 10)
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 40
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = fmt_exif_time(now_local)
    exif["Exif"][piexif.ExifIFD.DateTimeDigitized] = fmt_exif_time(now_local)
    exif["Exif"][piexif.ExifIFD.SubSecTimeOriginal] = f"{subsec:03d}"
    exif["Exif"][piexif.ExifIFD.FocalLength] = (55, 10)
    exif["Exif"][piexif.ExifIFD.ColorSpace] = 1
    exif["Exif"][piexif.ExifIFD.OffsetTime] = offset_str
    exif["Exif"][piexif.ExifIFD.OffsetTimeOriginal] = offset_str
    exif["Exif"][piexif.ExifIFD.OffsetTimeDigitized] = offset_str

    exif["GPS"][piexif.GPSIFD.GPSLatitudeRef] = "N" if lat_rand >= 0 else "S"
    exif["GPS"][piexif.GPSIFD.GPSLatitude] = decimal_to_exif_gps(lat_rand)
    exif["GPS"][piexif.GPSIFD.GPSLongitudeRef] = "E" if lon_rand >= 0 else "W"
    exif["GPS"][piexif.GPSIFD.GPSLongitude] = decimal_to_exif_gps(lon_rand)
    exif["GPS"][piexif.GPSIFD.GPSDateStamp] = now_utc.strftime("%Y:%m:%d")
    exif["GPS"][piexif.GPSIFD.GPSTimeStamp] = gps_time_tuple(now_utc)

    exif_bytes = piexif.dump(exif)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", exif=exif_bytes, quality=95)
    buffer.seek(0)

    filename = f"imagen_{now_local.strftime('%Y%m%d_%H%M%S')}.jpg"
    img_b64_out = base64.b64encode(buffer.read()).decode("utf-8")

    return jsonify({"filename": filename, "image_base64": img_b64_out})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
