# kyodai_cards_generator/app.py

from flask import Flask, render_template, request, send_file, redirect, url_for, make_response
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import zipfile
import uuid
import io
import random

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/cards"
DATA_CACHE = "static/data"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATA_CACHE, exist_ok=True)

try:
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(FONT_PATH, 32)
except:
    font = ImageFont.load_default()

def generate_card(data_row, output_path):
    img = Image.new("RGB", (800, 500), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 800, 80], fill="#222")
    draw.text((20, 20), "Torneo Kyodai 2025", fill="white", font=font)
    fields = [
        ("Nombre", data_row.get("Nombre y Apellido", "")),
        ("Categoría", data_row.get("Categoría", "")),
        ("Kata", data_row.get("Nombre Kata", "")),
        ("Tatami", str(data_row.get("Tatami", ""))),
        ("Pool", data_row.get("Pool", ""))
    ]
    y = 120
    for label, value in fields:
        draw.text((40, y), f"{label}: {value}", fill="#000", font=font)
        y += 60
    img.save(output_path)

def create_cards_from_excel(file_path, mode):
    df = pd.read_excel(file_path)
    zip_id = str(uuid.uuid4())
    zip_output = os.path.join(OUTPUT_FOLDER, f"cards_{zip_id}.zip")
    temp_dir = os.path.join(OUTPUT_FOLDER, f"temp_{zip_id}")
    os.makedirs(temp_dir, exist_ok=True)

    if mode == "individual":
        for _, row in df.iterrows():
            name = row.get("Nombre y Apellido", f"card_{uuid.uuid4()}")
            safe_name = "_".join(name.lower().split())
            output_path = os.path.join(temp_dir, f"{safe_name}.png")
            generate_card(row, output_path)

    elif mode == "categoria":
        grouped = df.groupby("Categoría")
        for categoria, group in grouped:
            img = Image.new("RGB", (1000, 100 + 80 * len(group)), color="white")
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, 1000, 80], fill="#004466")
            draw.text((20, 20), f"Categoría: {categoria}", fill="white", font=font)
            y = 100
            for _, row in group.iterrows():
                text = f"{row['Nombre y Apellido']} - Kata: {row['Nombre Kata']} - Tatami: {row['Tatami']} - Pool: {row['Pool']}"
                draw.text((40, y), text, fill="#000", font=font)
                y += 60
            safe_categoria = "_".join(categoria.lower().split())
            output_path = os.path.join(temp_dir, f"categoria_{safe_categoria}.png")
            img.save(output_path)

    with zipfile.ZipFile(zip_output, 'w') as zipf:
        for fname in os.listdir(temp_dir):
            zipf.write(os.path.join(temp_dir, fname), fname)

    return zip_output

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('archivo')
        mode = request.form.get('modo')
        titulo = request.form.get('titulo')

        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            df = pd.read_excel(filepath)
            session_id = str(uuid.uuid4())
            data_path = os.path.join(DATA_CACHE, f"{session_id}.csv")
            df.to_csv(data_path, index=False)
            return redirect(url_for('cards', session_id=session_id, title=titulo))
    return render_template("index.html")

@app.route('/cards/<session_id>')
def cards(session_id):
    data_path = os.path.join(DATA_CACHE, f"{session_id}.csv")
    if not os.path.exists(data_path):
        return "Datos no encontrados", 404
    df = pd.read_csv(data_path)
    title = request.args.get("title", "Torneo Kyodai")
    return render_template("cards.html", data=df.to_dict(orient="records"), title=title)

def generar_datos_dummy(n=6):
    NOMBRES = ["Lucía Ramos", "Diego Torres", "Valentina Gómez", "Luis Mendoza", "Sofía Romero", "Mateo López"]
    CATEGORIAS = ["4 años", "6-7 Principiantes", "8-9 Intermedios"]
    KATAS = ["Taikioku", "Heian Shodan", "Heian Nidan"]
    TATAMIS = [1, 2, 3, 4]
    POOLS = ["P1", "P2", "P3"]

    data = []
    for _ in range(n):
        data.append({
            "Nombre y Apellido": random.choice(NOMBRES),
            "Categoría": random.choice(CATEGORIAS),
            "Nombre Kata": random.choice(KATAS),
            "Tatami": random.choice(TATAMIS),
            "Pool": random.choice(POOLS)
        })
    return data

@app.route('/preview')
def preview():
    dummy_data = generar_datos_dummy(6)
    return render_template("cards.html", data=dummy_data, title="Vista de Ejemplo")

@app.route('/example.xlsx')
def descargar_ejemplo():
    dummy_data = generar_datos_dummy(10)
    df = pd.DataFrame(dummy_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Participantes')
    output.seek(0)
    response = make_response(output.read())
    response.headers["Content-Disposition"] = "attachment; filename=Ejemplo_Torneo_Kyodai.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
