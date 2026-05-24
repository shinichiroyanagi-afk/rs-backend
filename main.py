from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

THEME_ETF_LIST = [
    "WGMI", "BLOK", "ICLN", "QTUM", "CIBR", "TAN", "SMH", "IGV",
    "JETS", "UFO", "IPO", "BOAT", "ARKG", "ARKK", "ARKW",
    "XLK", "XLV", "XLE", "XLF", "XLI", "XLP", "XLU", "XLB", "XLC", "XLRE",
    "SPY", "QQQ", "IWM", "EEM", "GLD", "SLV", "USO",
    "SOXX", "HACK", "BOTZ", "ROBO", "FINX", "COPX", "SIL", "GDX",
]

SECTOR_ETF_LIST = [
    "RSPT", "RSPD", "RSPU", "RSPG", "RSPH",
    "RSPR", "RSPS", "RSPF", "RSPM", "RSPC", "RSPN",
]

SECTOR_NAMES = {
    "RSPT": "Technology", "RSPD": "Cons Disc", "RSPU": "Utilities",
    "RSPG": "Energy", "RSPH": "Health Care", "RSPR": "Real Estate",
    "RSPS": "Cons Staples", "RSPF": "Financials", "RSPM": "Materials",
    "RSPC": "Comm Svcs", "RSPN": "Industrials",
}

def calc_rs_score_at(close, offset=0):
    idx = -1 - offset
    try:
        r63  = float(close.pct_change(63).iloc[idx])
        r126 = float(close.pct_change(126).iloc[idx])
        r189 = float(close.pct_change(189).iloc[idx])
        r252 = float(close.pct_change(252).iloc[idx])
        score = (r63*2 + r126 + r189 + r252) / 5
        return None if pd.isna(score) else score
    except:
        return None

def build_rank_table(etf_list, sector_names=None):
    all_closes = {}
    for ticker in etf_list:
        df = yf.download(ticker, period="2y", auto_adjust=True, progress=False)
        if len(df) >= 252:
            all_closes[ticker] = df['Close'].squeeze()

    offsets = {"now": 0, "d1": 1, "w1": 5, "m1": 21}
    scores_by_offset = {}
    for label, offset in offsets.items():
        scores = {}
        for ticker, close in all_closes.items():
            score = calc_rs_score_at(close, offset)
            if score is not None:
                scores[ticker] = score
        scores_by_offset[label] = scores

    ranks_by_offset = {}
    for label, scores in scores_by_offset.items():
        s = pd.Series(scores)
        ranks_by_offset[label] = (s.rank(pct=True) * 100).round(0).astype(int).to_dict()

    rows = []
    for ticker, close in all_closes.items():
        price = round(float(close.iloc[-1]), 2)
        rs_day = round(float(close.pct_change(1).iloc[-1]) * 100, 2)
        rs_wk  = round(float(close.pct_change(5).iloc[-1]) * 100, 2)
        row = {
            "now":    ranks_by_offset["now"].get(ticker),
            "d1":     ranks_by_offset["d1"].get(ticker),
            "w1":     ranks_by_offset["w1"].get(ticker),
            "m1":     ranks_by_offset["m1"].get(ticker),
            "ticker": ticker,
            "price":  price,
            "rsDay":  rs_day,
            "rsWk":   rs_wk,
        }
        if sector_names:
            row["name"] = sector_names.get(ticker, "")
        if row["now"] is not None:
            rows.append(row)

    rows.sort(key=lambda x: x["now"], reverse=True)
    return rows

@app.get("/api/theme")
def get_theme():
    return build_rank_table(THEME_ETF_LIST)

@app.get("/api/sector")
def get_sector():
    return build_rank_table(SECTOR_ETF_LIST, SECTOR_NAMES)