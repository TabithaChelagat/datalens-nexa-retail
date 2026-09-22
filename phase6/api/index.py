import io
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler
import pandas as pd

DEMO_PATH = Path(__file__).resolve().parent.parent / "demo_data.json"

def load_demo():
    with DEMO_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def response(handler, status, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        response(self, 200, {"ok": True})

    def do_GET(self):
        if self.path.rstrip("/") == "/api/demo":
            try:
                return response(self, 200, load_demo())
            except Exception as exc:
                return response(self, 500, {"error": f"Demo data could not be loaded: {exc}"})
        return response(self, 404, {"error": "Route not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/profile":
            return response(self, 404, {"error": "Route not found"})
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return response(self, 400, {"error": "Upload a CSV or Excel file as multipart form data."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 8 * 1024 * 1024:
                return response(self, 413, {"error": "File exceeds the 8 MB demo limit."})
            boundary = content_type.split("boundary=", 1)[-1].encode()
            raw = self.rfile.read(length)
            file_bytes, filename = None, "upload"
            for part in raw.split(b"--" + boundary):
                if b"filename=" not in part or b"\r\n\r\n" not in part:
                    continue
                header, payload = part.split(b"\r\n\r\n", 1)
                filename = header.split(b'filename="', 1)[1].split(b'"', 1)[0].decode("utf-8", "ignore")
                file_bytes = payload.rsplit(b"\r\n", 1)[0]
                break
            if file_bytes is None:
                return response(self, 400, {"error": "No file found."})
            lower = filename.lower()
            if lower.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif lower.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                return response(self, 400, {"error": "Supported formats: CSV, XLSX, XLS."})
            preview = df.head(10).where(pd.notna(df.head(10)), None).to_dict(orient="records")
            return response(self, 200, {"filename":filename,"rows":int(df.shape[0]),"columns":int(df.shape[1]),"column_names":[str(c) for c in df.columns],"missing_cells":int(df.isna().sum().sum()),"duplicate_rows":int(df.duplicated().sum()),"numeric_columns":[str(c) for c in df.select_dtypes(include="number").columns],"preview":preview,"message":"Profile generated. This upload is isolated from the Nexa Retail demo dataset."})
        except Exception as exc:
            return response(self, 422, {"error": f"Could not read the file: {exc}"})
