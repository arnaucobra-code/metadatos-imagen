from flask import Flask, request, jsonify
import base64
import io
from PIL import Image
import piexif
import os

app = Flask(__name__)

# Función auxiliar para convertir coordenadas decimales a formato EXIF
def deg_to_dms_rational(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int((deg - d - m/60) * 3600 * 100)
    return ((d, 1), (m, 1), (s, 100))

@app.route("/procesar", methods=["POST"])
def procesar():
    try:
        data = request.get_json()
        image_b64 = data["image_base64"]
        lat = float(data["latitude"])
        lon = float(data["longitude"])

        # Decodificar imagen base64
        img_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_bytes))

        # Crear estructura EXIF
        exif_dict = {"GPS": {}}
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = deg_to_dms_rational(abs(lat))
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = deg_to_dms_rational(abs(lon))

        # Insertar EXIF en la imagen
        exif_bytes = piexif.dump(exif_dict)
        output = io.BytesIO()
        img.save(output, format="JPEG", exif=exif_bytes)
        output.seek(0)

        # Codificar de nuevo en base64 (opcional)
        new_b64 = base64.b64encode(output.read()).decode("utf-8")

        return jsonify({
            "status": "ok",
            "mensaje": "Imagen procesada correctamente",
            "image_base64": new_b64
        })

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
