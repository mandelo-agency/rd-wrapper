import os
import io
import hashlib
import requests
from flask import Flask, request, jsonify, send_file
from pdf2image import convert_from_bytes
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Cache: { hash: [page1_bytes, page2_bytes, ...] }
cache = {}

def convert_page(args):
    page, i = args
    page.thumbnail((1200, 1200))
    buffer = io.BytesIO()
    page.save(buffer, format='JPEG', quality=75, optimize=True)
    return buffer.getvalue()

@app.route('/pdf-pages', methods=['GET'])
def pdf_pages():
    pdf_url = request.args.get('url')

    if not pdf_url:
        return jsonify({'error': 'Geen URL meegegeven'}), 400

    # Hash van de URL als cache key
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()

    # Niet opnieuw converteren als al in cache
    if url_hash not in cache:
        try:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            pdf_bytes = response.content

            pages = convert_from_bytes(
                pdf_bytes,
                dpi=100,
                fmt='jpeg',
                thread_count=8,
                use_pdftocairo=True,
                size=(1200, None)
            )

            with ThreadPoolExecutor(max_workers=8) as executor:
                page_bytes = list(executor.map(convert_page, [(page, i) for i, page in enumerate(pages)]))

            cache[url_hash] = page_bytes

        except requests.RequestException as e:
            return jsonify({'error': f'PDF kon niet worden opgehaald: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': f'Fout bij verwerken: {str(e)}'}), 500

    # URLs teruggeven per pagina
    base_url = request.host_url.rstrip('/')
    results = [
        {
            'page': i + 1,
            'src': f'{base_url}/page/{url_hash}/{i + 1}.jpg'
        }
        for i in range(len(cache[url_hash]))
    ]

    return jsonify(results)


@app.route('/page/<url_hash>/<int:page_num>.jpg', methods=['GET'])
def serve_page(url_hash, page_num):
    if url_hash not in cache or page_num < 1 or page_num > len(cache[url_hash]):
        return 'Niet gevonden', 404

    img_bytes = cache[url_hash][page_num - 1]
    return send_file(io.BytesIO(img_bytes), mimetype='image/jpeg')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)