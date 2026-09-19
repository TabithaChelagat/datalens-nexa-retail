import io, json, os
from http.server import BaseHTTPRequestHandler
import pandas as pd

DEMO = {
    'name': 'Nexa Retail',
    'period': '2024-01-01 to 2025-12-31',
    'status': 'Validated demo dataset',
    'capabilities': ['Revenue and profit analysis', 'Data-quality reporting', 'Store/category analysis', 'Evidence-first answers']
}

def response(handler, status, payload):
    body = json.dumps(payload, default=str).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type')
    handler.end_headers()
    handler.wfile.write(body)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        response(self, 200, {'ok': True})

    def do_GET(self):
        if self.path.rstrip('/') == '/api/demo':
            return response(self, 200, DEMO)
        return response(self, 404, {'error': 'Route not found'})

    def do_POST(self):
        if self.path.rstrip('/') != '/api/profile':
            return response(self, 404, {'error': 'Route not found'})
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            return response(self, 400, {'error': 'Upload a CSV or Excel file as multipart form data.'})
        length = int(self.headers.get('Content-Length', '0'))
        if length > 8 * 1024 * 1024:
            return response(self, 413, {'error': 'File exceeds the 8 MB demo limit.'})
        # Minimal multipart parser for the Vercel demo endpoint.
        boundary = content_type.split('boundary=', 1)[-1].encode()
        raw = self.rfile.read(length)
        parts = raw.split(b'--' + boundary)
        file_bytes, filename = None, 'upload'
        for part in parts:
            if b'filename=' not in part:
                continue
            header, payload = part.split(b'\r\n\r\n', 1)
            filename_part = header.split(b'filename="', 1)[1].split(b'"', 1)[0]
            filename = filename_part.decode('utf-8', 'ignore')
            file_bytes = payload.rsplit(b'\r\n', 1)[0]
            break
        if file_bytes is None:
            return response(self, 400, {'error': 'No file found.'})
        try:
            lower = filename.lower()
            if lower.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif lower.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                return response(self, 400, {'error': 'Supported formats: CSV, XLSX, XLS.'})
            missing = int(df.isna().sum().sum())
            duplicate_rows = int(df.duplicated().sum())
            profile = {
                'filename': filename,
                'rows': int(df.shape[0]),
                'columns': int(df.shape[1]),
                'column_names': [str(c) for c in df.columns],
                'missing_cells': missing,
                'duplicate_rows': duplicate_rows,
                'numeric_columns': [str(c) for c in df.select_dtypes(include='number').columns],
                'preview': df.head(10).where(pd.notna(df.head(10)), None).to_dict(orient='records'),
                'message': 'Profile generated. This upload is isolated from the Nexa Retail demo dataset.'
            }
            return response(self, 200, profile)
        except Exception as exc:
            return response(self, 422, {'error': f'Could not read the file: {exc}'})
