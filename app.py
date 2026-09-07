from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="SharePlate")

BASE_DIR = Path(__file__).resolve().parent

# Serve CSS and JavaScript
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


@app.get("/", response_class=HTMLResponse)
def donor_dashboard():

    html_file = BASE_DIR / "templates" / "donor.html"

    return html_file.read_text(encoding="utf-8")


@app.get("/ngo", response_class=HTMLResponse)
def ngo_dashboard():

    html_file = BASE_DIR / "templates" / "ngo.html"

    return html_file.read_text(encoding="utf-8")