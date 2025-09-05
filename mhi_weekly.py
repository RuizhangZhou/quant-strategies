# mhi_weekly.py
# 功能：周频抓数据 -> 计算MHI(市场温度计) -> 给出本周目标权重/买卖建议 -> 可选回测
# 依赖：yfinance, pandas, numpy, backtrader, python-dotenv, requests-cache, (可选) fredapi

import os, sys, datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf
import backtrader as bt
from dataclasses import dataclass
from dotenv import load_dotenv

# ---------- 基本设置（可按"更保守"口味微调） ----------
START = "2015-01-01"
BASE_WEIGHTS   = {"SPY":0.35, "GLD":0.45, "BTC":0.10, "CASH":0.10}
LOW_MHI_WEI    = {"SPY":0.55, "GLD":0.25, "BTC":0.05, "CASH":0.15}
HIGH_MHI_WEI   = {"SPY":0.15, "GLD":0.60, "BTC":0.05, "CASH":0.20}

# 现金上限
CASH_MAX = 0.35          # 提高现金上限到35%

# 微调参数（优化为低频高量）
MIN_CHANGE = 0.08        # 8%以下调仓不动作（减少小幅调整）
CONFIRM_WEEKS = 3        # "三周确认"机制（增强信号确认）
COMFORT_ZONE = 0.05      # 舒适区间：目标权重±5%内不调仓
COMMISSION = 0.0005      # 5bps手续费
USE_REAL_YIELD_TILT = True   # 启用真实利率拨杆
USE_HY_OAS_IN_MHI   = True   # MHI中启用高收益债利差

# ---------- Tickers ----------
TICKERS_YF = {
    "SPY": "SPY",     # S&P500
    "GLD": "GLD",     # 黄金
    "BTC": "BTC-USD", # 比特币
    "VIX": "^VIX"     # 恐慌指数
}

# 11个大板块ETF用于市场广度计算
SECTORS = ["XLY","XLP","XLE","XLF","XLV","XLI","XLB","XLRE","XLK","XLU","XLC"]  # 11大板块ETF

# ---------- 小工具 ----------
def weekly_last(df):    # 周五收盘采样
    return df.resample("W-FRI").last().dropna(how="all")

def zscore(series, window=260):
    return (series - series.rolling(window).mean()) / series.rolling(window).std(ddof=0)

def dl_yf(cols, start=START):
    data = yf.download(cols, start=start, auto_adjust=True, progress=False)["Close"]
    return data if isinstance(data, pd.DataFrame) else data.to_frame()

def compute_breadth(sector_w):
    ma = sector_w.rolling(40).mean()                  # 约等于200个交易日的周均线
    above = (sector_w > ma).astype(float)
    return above.mean(axis=1).rename("breadth")       # 0~1

# ---------- 可选：FRED 序列 ----------
def load_fred_series():
    load_dotenv()
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        return None, None
    try:
        from fredapi import Fred
        fred = Fred(api_key=key)
        # 10Y TIPS 真实利率（日频）
        ry = fred.get_series("DFII10").to_frame("real_yield")
        ry_w = weekly_last(ry)["real_yield"]
        # 高收益债利差（日频）
        oas = fred.get_series("BAMLH0A0HYM2").to_frame("hy_oas")
        oas_w = weekly_last(oas)["hy_oas"]
        return ry_w, oas_w
    except Exception as e:
        print("[WARN] FRED unavailable:", e)
        return None, None

# ---------- 构建 MHI ----------
def build_mhi():
    px = dl_yf(list(TICKERS_YF.values()) + SECTORS)
    px_w = weekly_last(px)
    price_w = px_w[[TICKERS_YF["SPY"],TICKERS_YF["GLD"],TICKERS_YF["BTC"]]].rename(
        columns={TICKERS_YF["SPY"]:"SPY", TICKERS_YF["GLD"]:"GLD", TICKERS_YF["BTC"]:"BTC"})
    vix_w   = px_w[TICKERS_YF["VIX"]].rename("VIX")
    sectors = px_w[SECTORS]

    z_vix = zscore(vix_w).rename("z_vix")
    breadth = compute_breadth(sectors)
    z_breadth = zscore(breadth).rename("z_breadth")

    # Frenzy 分=自满/过热：低VIX、高广度 -> frenzy = -z(VIX) + z(breadth)
    frenzy_parts = [(-z_vix).rename("frenzy_vix"), z_breadth.rename("frenzy_breadth")]

    ry_w, oas_w = load_fred_series()
    if USE_HY_OAS_IN_MHI and oas_w is not None:
        frenzy_parts.append((-zscore(oas_w)).rename("frenzy_hyoas"))  # 利差小=自满

    frenzy_df = pd.concat(frenzy_parts, axis=1).dropna()
    mhi = frenzy_df.mean(axis=1).rename("MHI")   # 越高越"疯狂"

    return price_w.loc[mhi.index], mhi, ry_w

# ---------- 目标权重与拨杆 ----------
def pick_weights(mhi_val):
    # 调整阈值，平衡调仓频率 (±1.75)
    if mhi_val <= -1.75:
        bucket, target = "LOW", LOW_MHI_WEI.copy()
    elif mhi_val >= 1.75:
        bucket, target = "HIGH", HIGH_MHI_WEI.copy()
    else:
        bucket, target = "NEUTRAL", BASE_WEIGHTS.copy()
    # 现金上限保护
    target["CASH"] = min(target.get("CASH",0.0), CASH_MAX)
    # 三资产权重重新归一（现金之外）
    s = target["SPY"]+target["GLD"]+target["BTC"]
    if s > 0:
        scale = (1 - target["CASH"]) / s
        for k in ["SPY","GLD","BTC"]:
            target[k] = max(0.0, target[k]*scale)
    return bucket, target

def apply_real_yield_tilt(target, real_yield_w, ref_date):
    if not (USE_REAL_YIELD_TILT and real_yield_w is not None and ref_date in real_yield_w.index):
        return target
    idx = real_yield_w.index.get_loc(ref_date)
    if idx >= 4:
        delta = real_yield_w.iloc[idx] - real_yield_w.iloc[idx-4]
        # 阈值：±0.20个百分点（可调）
        if delta <= -0.20:   # 真实利率下行 -> 金+10%、股-10%
            target["GLD"] = min(1.0, target["GLD"] + 0.10); target["SPY"] = max(0.0, target["SPY"] - 0.10)
        elif delta >= 0.20:  # 上行 -> 股+10%、金-10%
            target["SPY"] = min(1.0, target["SPY"] + 0.10); target["GLD"] = max(0.0, target["GLD"] - 0.10)
        # 再做一次现金上限与归一
        return pick_weights(0)[1] | {"SPY":target["SPY"],"GLD":target["GLD"],"BTC":target["BTC"],"CASH":target.get("CASH",0.0)}
    return target

# ---------- 生成"买/卖建议"（输入当前持仓权重，输出目标与差额） ----------
def advise(current_weights:dict):
    price_w, mhi, ry_w = build_mhi()
    # 取最近一个周五
    ref_date = mhi.index[-1]
    mhi_val = float(mhi.iloc[-1])
    bucket, target = pick_weights(mhi_val)
    target = apply_real_yield_tilt(target, ry_w, ref_date)

    # 三周确认：检查过去三周是否都是同一分档
    if len(mhi) >= CONFIRM_WEEKS:
        recent_buckets = []
        for i in range(1, CONFIRM_WEEKS + 1):
            recent_bucket, _ = pick_weights(float(mhi.iloc[-i]))
            recent_buckets.append(recent_bucket)
        confirmed = len(set(recent_buckets)) == 1  # 所有分档都相同
    else:
        confirmed = True

    delta = {k: round(target[k] - current_weights.get(k,0.0), 4) for k in ["SPY","GLD","BTC","CASH"]}
    
    # 只在极端MHI条件下调仓，忽略舒适区间
    if bucket == "NEUTRAL":
        # 如果是中性区间，不调仓
        delta = {k: 0.0 for k in ["SPY","GLD","BTC","CASH"]}
        print("MHI in neutral zone, no rebalancing needed.")
    else:
        # 只在极端情况下(LOW/HIGH)才考虑最小变动阈值
        for k in delta:
            if abs(delta[k]) < MIN_CHANGE:
                delta[k] = 0.0

    print(f"[{ref_date.date()}] MHI={mhi_val:.2f} bucket={bucket} confirmed={confirmed}")
    print("Target weights:", target)
    print("Delta vs current (>0 buy, <0 sell):", delta)
    if not confirmed:
        print("(Note: Two-week confirmation not met, you may wait this week.)")
    return target, delta, confirmed

# ---------- 可选：简单回测 ----------
class PandasData(bt.feeds.PandasData):
    params = (("datetime", None), ("open",-1),("high",-1),("low",-1),("close",0),("volume",-1),("openinterest",-1))

class WeeklyRebal(bt.Strategy):
    params = dict(mhi=None, ry=None)

    def __init__(self):
        self.mhi = self.p.mhi
        self.ry = self.p.ry
        self.recent_bins = []

    def next(self):
        dtc = self.data0.datetime.date(0)
        if dtc.weekday() != 0:  # 周一再平衡
            return
        ref_date = dtc - dt.timedelta(days=3)  # 上周五
        if ref_date not in self.mhi.index:
            ref_date = self.mhi.index[self.mhi.index.get_loc(ref_date, method="pad")]
        m = float(self.mhi.loc[ref_date])
        bucket, target = pick_weights(m)
        self.recent_bins.append(bucket); self.recent_bins = self.recent_bins[-CONFIRM_WEEKS:]
        if len(self.recent_bins)<CONFIRM_WEEKS or len(set(self.recent_bins))>1:
            return
        target = apply_real_yield_tilt(target, self.ry, ref_date)

        # 现金 = 1 - 三资产
        w_spy, w_gld, w_btc = target["SPY"], target["GLD"], target["BTC"]
        total = self.broker.getvalue()
        for name in ["SPY","GLD","BTC"]:
            data = [d for d in self.datas if d._name==name][0]
            cur = self.getposition(data).size * data.close[0] / total if total>0 else 0.0
            tgt = {"SPY":w_spy,"GLD":w_gld,"BTC":w_btc}[name]
            if abs(tgt-cur) >= MIN_CHANGE:
                self.order_target_percent(data, tgt)

def backtest():
    price_w, mhi, ry_w = build_mhi()
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000); cerebro.broker.setcommission(commission=COMMISSION)
    for col in ["SPY","GLD","BTC"]:
        df = price_w[[col]].dropna().copy(); df.columns = ["Close"]
        cerebro.adddata(PandasData(dataname=df, name=col))
    cerebro.addstrategy(WeeklyRebal, mhi=mhi, ry=ry_w)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sr", timeframe=bt.TimeFrame.Weeks, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    res = cerebro.run()[0]
    print("\n=== Backtest Stats ===")
    print("Final portfolio value:", round(cerebro.broker.getvalue(),2))
    print("Sharpe Ratio (A):", res.analyzers.sr.get_analysis().get("sharperatio"))
    dd = res.analyzers.dd.get_analysis().max
    print("Max Drawdown %:", round(dd.drawdown,2) if dd else None)

if __name__=="__main__":
    # 用法:
    # 1) 建议模式(输入当前仓位；百分比之和<=1，余下视作现金)
    #    python mhi_weekly.py advise 0.4 0.4 0.2
    #    顺序=SPY GLD BTC；如果不填，默认全现金
    # 2) 回测模式:
    #    python mhi_weekly.py backtest
    if len(sys.argv)>=2 and sys.argv[1]=="advise":
        vals = [float(x) for x in sys.argv[2:5]] if len(sys.argv)>=5 else [0.0,0.0,0.0]
        cur = {"SPY":vals[0], "GLD":vals[1], "BTC":vals[2]}
        cur["CASH"] = max(0.0, 1.0 - sum(vals))
        advise(cur)
    else:
        backtest()