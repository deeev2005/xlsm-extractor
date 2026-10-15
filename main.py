import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from oletools.olevba import VBA_Parser

app = FastAPI()
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB Limit

# 1. Set this environment variable in your Render Dashboard
API_KEY = os.environ.get("RENDER_API_SECRET", "change-this-to-a-secure-random-string")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized API access.")
    return api_key

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://script.google.com"], # Restricted to Google Apps Script environment
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

@app.api_route("/health", methods=["GET", "HEAD", "POST", "OPTIONS"])
@app.api_route("/status", methods=["GET", "HEAD", "POST", "OPTIONS"])
def health_check():
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_time = datetime.now(ist_tz).strftime("%d/%m/%Y, %I:%M:%S %p")
    return {
        "status": "ok",
        "service": "xlsm-extractor",
        "timeIST": ist_time,
    }

@app.api_route("/ping", methods=["GET", "HEAD", "POST", "OPTIONS"], response_class=PlainTextResponse)
def ping():
    return "OK"

@app.post("/extract-vba")
async def extract_vba(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    try:
        file_bytes = bytearray()
        
        # 2. Read in 1MB chunks to monitor memory limits safely
        while chunk := await file.read(1024 * 1024):
            file_bytes.extend(chunk)
            if len(file_bytes) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File size exceeds the 25MB limit.")

        if not file_bytes:
            raise HTTPException(status_code=400, detail="No file data received.")
            
        # Parse the binary stream from memory
        vba_parser = VBA_Parser(file.filename, data=bytes(file_bytes))
        
        if not vba_parser.detect_vba_macros():
            return {"error": "No VBA macros found in this file."}
            
        extracted_code = ""
        for (filename, stream_path, vba_filename, vba_code) in vba_parser.extract_macros():
            extracted_code += f"' --- Macro from {vba_filename} ---\n{vba_code}\n\n"
            
        vba_parser.close()
        return {"vba": extracted_code}
        
    except HTTPException:
        raise # Pass intended HTTP errors through
    except Exception as e:
        # 3. Log the actual error to Render console, but hide it from the public response
        logging.error(f"VBA Extraction Failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during extraction.")
