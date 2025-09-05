# benchmark_analysis.py
# 对比分析：MHI策略 vs 买入持有策略 vs 各单一资产

import pandas as pd
import numpy as np
import yfinance as yf
# import matplotlib.pyplot as plt  # 暂时注释掉
from mhi_weekly import build_mhi, pick_weights, apply_real_yield_tilt

def calculate_returns(prices):
    """计算收益率"""
    return prices.pct_change().fillna(0)

def calculate_metrics(returns):
    """计算关键指标"""
    # 计算累积收益
    cumulative_returns = (1 + returns).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1
    
    # 年化收益率 (周频数据，一年约52周)
    years = len(returns) / 52
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
    
    # 年化波动率
    annual_vol = returns.std() * np.sqrt(52)
    
    # 夏普比率
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # 最大回撤
    max_dd = (cumulative_returns / cumulative_returns.cummax() - 1).min()
    
    return {
        'Total Return': f"{total_return:.1%}",
        'Annual Return': f"{annual_return:.1%}", 
        'Annual Vol': f"{annual_vol:.1%}",
        'Sharpe Ratio': f"{sharpe:.2f}",
        'Max Drawdown': f"{max_dd:.1%}"
    }

def simulate_strategy():
    """模拟MHI策略"""
    price_w, mhi, ry_w = build_mhi()
    
    # 初始权重
    portfolio_value = [100000]
    current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
    
    strategy_returns = []
    rebalance_dates = []
    
    for i in range(1, len(price_w)):
        date = price_w.index[i]
        
        # 计算当期资产收益
        spy_ret = price_w["SPY"].iloc[i] / price_w["SPY"].iloc[i-1] - 1
        gld_ret = price_w["GLD"].iloc[i] / price_w["GLD"].iloc[i-1] - 1 
        btc_ret = price_w["BTC"].iloc[i] / price_w["BTC"].iloc[i-1] - 1
        
        # 计算组合收益
        portfolio_ret = (current_weights["SPY"] * spy_ret + 
                        current_weights["GLD"] * gld_ret + 
                        current_weights["BTC"] * btc_ret)
        
        strategy_returns.append(portfolio_ret)
        portfolio_value.append(portfolio_value[-1] * (1 + portfolio_ret))
        
        # 检查是否需要调仓（每4周检查一次）
        if i % 4 == 0 and i < len(mhi):
            mhi_val = float(mhi.iloc[i])
            bucket, target = pick_weights(mhi_val)
            target = apply_real_yield_tilt(target, ry_w, date)
            
            # 检查确认机制
            if i >= 12:  # 至少3个月数据
                recent_buckets = []
                for j in range(1, 4):
                    if i-j*4 >= 0 and i-j*4 < len(mhi):
                        recent_bucket, _ = pick_weights(float(mhi.iloc[i-j*4]))
                        recent_buckets.append(recent_bucket)
                
                if len(set(recent_buckets)) == 1:  # 确认信号
                    # 只在极端MHI条件下调仓
                    need_rebalance = (bucket != "NEUTRAL")
                    
                    if need_rebalance:
                        current_weights = target.copy()
                        rebalance_dates.append(date)
    
    return pd.Series(strategy_returns, index=price_w.index[1:]), rebalance_dates

def main():
    print("=== 2020-2025 Backtest Comparison Analysis ===\n")
    
    # 获取数据并运行策略
    price_w, mhi, ry_w = build_mhi()
    strategy_returns, rebalance_dates = simulate_strategy()
    
    # 计算基准收益
    asset_returns = calculate_returns(price_w)
    
    # 等权重组合 (33.3%每个)
    equal_weight_returns = (asset_returns["SPY"] * 0.333 + 
                           asset_returns["GLD"] * 0.333 + 
                           asset_returns["BTC"] * 0.334)
    
    # 基础权重组合 (固定35% SPY, 45% GLD, 20% BTC)
    base_weight_returns = (asset_returns["SPY"] * 0.35 + 
                          asset_returns["GLD"] * 0.45 + 
                          asset_returns["BTC"] * 0.20)
    
    # 计算指标
    results = {}
    results["MHI_Strategy"] = calculate_metrics(strategy_returns)
    results["SPY_Only"] = calculate_metrics(asset_returns["SPY"])
    results["GLD_Only"] = calculate_metrics(asset_returns["GLD"])  
    results["BTC_Only"] = calculate_metrics(asset_returns["BTC"])
    results["Equal_Weight"] = calculate_metrics(equal_weight_returns)
    results["Base_Weight"] = calculate_metrics(base_weight_returns)
    
    # 打印结果
    df_results = pd.DataFrame(results).T
    print(df_results)
    
    print(f"\n=== Strategy Analysis ===")
    print(f"Rebalance count: {len(rebalance_dates)}")
    print(f"Rebalance frequency: Every {len(strategy_returns)/len(rebalance_dates):.1f} weeks" if rebalance_dates else "No rebalancing occurred")
    
    # 计算累积收益对比
    mhi_cumret = (1 + strategy_returns).cumprod()
    spy_cumret = (1 + asset_returns["SPY"]).cumprod()
    btc_cumret = (1 + asset_returns["BTC"]).cumprod()
    equal_cumret = (1 + equal_weight_returns).cumprod()
    
    print(f"\n=== Cumulative Returns Comparison ===")
    print(f"MHI Strategy Final Return: {mhi_cumret.iloc[-1] - 1:.1%}")
    print(f"SPY Final Return: {spy_cumret.iloc[-1] - 1:.1%}")
    print(f"BTC Final Return: {btc_cumret.iloc[-1] - 1:.1%}")
    print(f"Equal Weight Portfolio Final Return: {equal_cumret.iloc[-1] - 1:.1%}")
    
    return results

if __name__ == "__main__":
    main()