import os
import io
import requests
from flask import Flask, request, jsonify
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor
import base64

app = Flask(__name__)

def convert_page(args):
    page, i = args
    buffer = io.BytesIO()
    page.save(buffer, format='JPEG', quality=80)
    return {
        'page': i + 1,
        'image': f'data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}'
    }

@app.route('/pdf-pages', methods=['GET'])
def pdf_pages():
    pdf_url = request.args.get('url')

    if not pdf_url:
        return jsonify({'error': 'Geen URL meegegeven'}), 400

    try:
        # PDF ophalen
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        # Alle paginas tegelijk converteren met lage DPI voor snelheid
        pages = convert_from_bytes(
            response.content,
            dpi=120,          # lager = sneller
            fmt='jpeg',
            thread_count=6,   # meerdere threads tegelijk
            use_pdftocairo=True  # sneller dan pdftoppm
        )

        # Paginas parallel verwerken
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(convert_page, [(page, i) for i, page in enumerate(pages)]))

        return jsonify(results)

    except requests.RequestException as e:
        return jsonify({'error': f'PDF kon niet worden opgehaald: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Fout bij verwerken: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)