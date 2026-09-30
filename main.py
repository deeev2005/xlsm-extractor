from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from oletools.olevba import VBA_Parser

app = FastAPI()

# Automatically handle CORS for your Apps Script frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/extract-vba")
async def extract_vba(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="No file data received.")
            
        # Parse the binary stream
        vba_parser = VBA_Parser(file.filename, data=content)
        
        if not vba_parser.detect_vba_macros():
            return {"error": "No VBA macros found in this file."}
            
        extracted_code = ""
        for (filename, stream_path, vba_filename, vba_code) in vba_parser.extract_macros():
            extracted_code += f"' --- Macro from {vba_filename} ---\n{vba_code}\n\n"
            
        vba_parser.close()
        return {"vba": extracted_code}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
