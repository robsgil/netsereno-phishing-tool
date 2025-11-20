import os
import json
import email
from email import policy
from email.parser import BytesParser
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
from dotenv import load_dotenv
from fpdf import FPDF
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- HELPER FUNCTIONS ---

def extract_content(file_storage, content_type):
    """Extracts subject, sender, and body from uploaded files."""
    try:
        if "text" in content_type or file_storage.filename.endswith('.txt'):
            return {
                "subject": "Texto pegado / Archivo de texto",
                "sender": "Desconocido (Texto plano)",
                "body": file_storage.read().decode('utf-8', errors='ignore')
            }
        
        # Handle .eml files
        if file_storage.filename.endswith('.eml'):
            msg = BytesParser(policy=policy.default).parse(file_storage)
            body = msg.get_body(preferencelist=('plain', 'html'))
            body_content = body.get_content() if body else "No se pudo extraer el cuerpo."
            
            return {
                "subject": msg.get('subject', 'Sin asunto'),
                "sender": msg.get('from', 'Desconocido'),
                "body": body_content
            }
            
        return None
    except Exception as e:
        return {"error": str(e)}

def analyze_phishing(email_data):
    """Sends content to Gemini for analysis."""
    
    prompt = f"""
    Actúa como un experto en ciberseguridad de la marca 'NetSereno'. Tu trabajo es analizar correos sospechosos para audiencia española.
    
    Analiza el siguiente contenido de correo electrónico:
    ASUNTO: {email_data['subject']}
    REMITENTE: {email_data['sender']}
    CUERPO: {email_data['body']}[:3000] 

    Tareas:
    1. Evalúa la probabilidad de que sea Phishing (0-100).
    2. Identifica urgencia, errores gramaticales (típicos de traducciones malas al español), suplantación de identidad (Correos, Hacienda, Bancos, Bizum).
    3. Analiza la coherencia del remitente vs el contenido.

    Responde ÚNICAMENTE con un objeto JSON válido con esta estructura (sin markdown):
    {{
        "score": integer (0 a 100),
        "verdict": "string (SEGURO / SOSPECHOSO / PELIGROSO)",
        "summary": "string (Resumen corto en español para el usuario)",
        "reasons": ["string", "string", "string"] (3 puntos clave de por qué)
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean response to ensure valid JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        return {
            "score": 0, 
            "verdict": "ERROR", 
            "summary": "No se pudo analizar el correo. Inténtalo de nuevo.", 
            "reasons": [str(e)]
        }

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = {}
    
    # Handle File Upload
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        data = extract_content(file, file.content_type)
    # Handle Paste Text
    elif 'text_content' in request.form and request.form['text_content'].strip() != '':
        data = {
            "subject": "Texto Manual", 
            "sender": "N/A", 
            "body": request.form['text_content']
        }
    else:
        return jsonify({"error": "No se proporcionó ningún contenido."}), 400

    if not data or "error" in data:
        return jsonify({"error": "Formato de archivo no soportado o corrupto."}), 400

    # Perform Analysis
    analysis = analyze_phishing(data)
    
    # Return combined result
    return jsonify({
        "meta": data,
        "analysis": analysis
    })

@app.route('/download_report', methods=['POST'])
def download_report():
    req_data = request.json
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 51, 102) # NetSereno Blue
    pdf.cell(0, 10, "NetSereno - Informe de Ciberseguridad", ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Iluminando tus emails sospechosos", ln=True, align='C')
    pdf.ln(10)
    
    # Verdict
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Veredicto: {req_data['verdict']} (Probabilidad: {req_data['score']}%)", ln=True)
    
    # Details
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, f"Resumen: {req_data['summary']}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Factores de Riesgo Detectados:", ln=True)
    pdf.set_font("Arial", '', 11)
    for reason in req_data['reasons']:
        pdf.cell(0, 10, f"- {reason}", ln=True)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "Aviso Legal: Este informe es generado por IA y análisis estático. No garantiza el 100% de precisión. NetSereno no almacena sus correos.")
    
    buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1', 'replace')
    buffer.write(pdf_output)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name='NetSereno_Reporte.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)