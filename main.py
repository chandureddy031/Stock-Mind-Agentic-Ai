import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from agents import run_graph
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="StockMind")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, ticker: str = Form(...)):
    try:
        result = run_graph(ticker.strip())
        error = None
    except Exception as e:
        result = None
        error = str(e)
    return templates.TemplateResponse("index.html", {
        "request":      request,
        "result":       result,
        "error":        error,
        "query_ticker": ticker,
    })