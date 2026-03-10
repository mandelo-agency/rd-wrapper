import os
import io
import requests
from flask import Flask, request, jsonify
from pdf2image import convert_from_bytes
import base64

app = Flask(__name__)

@app.route('/pdf-pages', methods=['GET'])
def pdf_pages():
    pdf_url = request.args.get('url')

    if not pdf_url:
        return jsonify({'error': 'Geen URL meegegeven'}), 400

    try:
        # PDF ophalen
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        # Elke pagina omzetten naar JPG
        pages = convert_from_bytes(response.content, dpi=150, fmt='jpeg')

        result = []
        for i, page in enumerate(pages):
            buffer = io.BytesIO()
            page.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            result.append({
                'page': i + 1,
                'image': f'data:image/jpeg;base64,{img_base64}'
            })

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({'error': f'PDF kon niet worden opgehaald: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Fout bij verwerken: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
