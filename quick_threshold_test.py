# quick_threshold_test.py  
# 快速测试关键阈值组合（避免重复下载数据）

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi, apply_real_yield_tilt

def pick_weights_custom(mhi_val, low_threshold, high_threshold):
    """自定义正负阈值的权重选择函数"""
    BASE_WEIGHTS = {"SPY":0.35, "GLD":0.45, "BTC":0.10, "CASH":0.10}
    LOW_MHI_WEI = {"SPY":0.55, "GLD":0.25, "BTC":0.05, "CASH":0.15}  
    HIGH_MHI_WEI = {"SPY":0.15, "GLD":0.60, "BTC":0.05, "CASH":0.20}
    CASH_MAX = 0.35
    
    if mhi_val <= low_threshold:  # 注意：low_threshold是负数
        bucket, target = "LOW", LOW_MHI_WEI.copy()
    elif mhi_val >= high_threshold:  # high_threshold是正数
        bucket, target = "HIGH", HIGH_MHI_WEI.copy()
    else:
        bucket, target = "NEUTRAL", BASE_WEIGHTS.copy()
    
    # 现金上限保护和归一化
    target["CASH"] = min(target.get("CASH",0.0), CASH_MAX)
    s = target["SPY"]+target["GLD"]+target["BTC"]
    if s > 0:
        scale = (1 - target["CASH"]) / s
        for k in ["SPY","GLD","BTC"]:
            target[k] = max(0.0, target[k]*scale)
    
    return bucket, target

def calculate_trading_costs(old_weights, new_weights):
    """计算交易成本占比"""
    # 实际交易成本（滑点+手续费+价差）
    TOTAL_TRADING_COSTS = {
        "SPY": 0.0008,   # 0.08%
        "GLD": 0.0015,   # 0.15% 
        "BTC": 0.0040,   # 0.40% (最贵)
        "CASH": 0.0000
    }
    
    total_cost = 0.0
    for asset in ["SPY", "GLD", "BTC", "CASH"]:
        weight_change = abs(new_weights.get(asset, 0.0) - old_weights.get(asset, 0.0))
        total_cost += weight_change * TOTAL_TRADING_COSTS[asset]
    
    return total_cost

def test_key_combinations():
    """测试关键的正负阈值组合"""
    print("=== Quick Threshold Test (With Trading Costs) ===\n")
    
    # 重点测试的组合
    test_combinations = [
        # 对称组合
        (-1.3, 1.3), (-1.4, 1.4), (-1.5, 1.5), (-1.6, 1.6), (-1.7, 1.7), (-1.8, 1.8),
        # 负阈值更严格(更难触发防守)
        (-1.3, 1.5), (-1.3, 1.6), (-1.4, 1.6), (-1.4, 1.7), (-1.5, 1.7), (-1.5, 1.8),
        # 正阈值更严格(更难触发进攻) 
        (-1.5, 1.3), (-1.6, 1.3), (-1.6, 1.4), (-1.7, 1.4), (-1.7, 1.5), (-1.8, 1.5),
        # 极端组合
        (-1.2, 1.9), (-1.2, 2.0), (-1.9, 1.2), (-2.0, 1.2)
    ]
    
    # 一次性获取数据
    price_w, mhi, ry_w = build_mhi()
    
    print("Testing combinations:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count | Trading_Costs")
    print("-" * 100)
    
    results = []
    
    for low_thresh, high_thresh in test_combinations:
        # 模拟策略
        current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
        strategy_returns = []
        rebalance_count = 0
        total_trading_costs = 0.0
        
        for i in range(1, len(price_w)):
            date = price_w.index[i]
            
            # 计算资产收益
            spy_ret = price_w["SPY"].iloc[i] / price_w["SPY"].iloc[i-1] - 1
            gld_ret = price_w["GLD"].iloc[i] / price_w["GLD"].iloc[i-1] - 1 
            btc_ret = price_w["BTC"].iloc[i] / price_w["BTC"].iloc[i-1] - 1
            
            # 组合收益
            gross_portfolio_ret = (current_weights["SPY"] * spy_ret + 
                                  current_weights["GLD"] * gld_ret + 
                                  current_weights["BTC"] * btc_ret)
            
            net_portfolio_ret = gross_portfolio_ret
            
            # 每4周检查调仓
            if i % 4 == 0 and i < len(mhi) and i >= 12:
                mhi_val = float(mhi.iloc[i])
                bucket, target = pick_weights_custom(mhi_val, low_thresh, high_thresh)
                target = apply_real_yield_tilt(target, ry_w, date)
                
                # 三周确认机制
                recent_buckets = []
                for j in range(1, 4):
                    if i-j*4 >= 0 and i-j*4 < len(mhi):
                        recent_bucket, _ = pick_weights_custom(float(mhi.iloc[i-j*4]), low_thresh, high_thresh)
                        recent_buckets.append(recent_bucket)
                
                if len(set(recent_buckets)) == 1 and bucket != "NEUTRAL":
                    # 计算并扣除交易成本
                    trading_cost = calculate_trading_costs(current_weights, target)
                    net_portfolio_ret -= trading_cost
                    total_trading_costs += trading_cost
                    
                    current_weights = target.copy()
                    rebalance_count += 1
            
            strategy_returns.append(net_portfolio_ret)
        
        # 计算指标
        strategy_series = pd.Series(strategy_returns, index=price_w.index[1:])
        cumret = (1 + strategy_series).cumprod()
        total_return = cumret.iloc[-1] - 1
        years = len(strategy_series) / 52
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        annual_vol = strategy_series.std() * np.sqrt(52)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        max_dd = (cumret / cumret.cummax() - 1).min()
        
        result = {
            'low_threshold': low_thresh,
            'high_threshold': high_thresh,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'rebalance_count': rebalance_count,
            'total_trading_costs': total_trading_costs
        }
        results.append(result)
        
        print(f"    {low_thresh:4.1f}   |     {high_thresh:4.1f}    |   {total_return:5.1%}   |    {annual_return:5.1%}   |  {sharpe:4.2f}  | {max_dd:5.1%}  |      {rebalance_count}      |    {total_trading_costs:5.2%}")
    
    # 找出最佳组合
    print(f"\n=== TOP PERFORMERS ===\n")
    
    best_sharpe = sorted(results, key=lambda x: x['sharpe'], reverse=True)[:5]
    print("Top 5 by Sharpe Ratio:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count | Trading_Costs")
    print("-" * 100)
    for r in best_sharpe:
        print(f"    {r['low_threshold']:4.1f}   |     {r['high_threshold']:4.1f}    |   {r['total_return']:5.1%}   |    {r['annual_return']:5.1%}   |  {r['sharpe']:4.2f}  | {r['max_dd']:5.1%}  |      {r['rebalance_count']}      |    {r['total_trading_costs']:5.2%}")
    
    print(f"\n=== ANALYSIS ===\n")
    
    # 分析最优负阈值
    neg_analysis = {}
    for r in results:
        neg = r['low_threshold']
        if neg not in neg_analysis:
            neg_analysis[neg] = []
        neg_analysis[neg].append(r)
    
    print("Best positive threshold for each negative threshold:")
    print("Neg_Thresh | Best_Pos | Sharpe | Rebal_Count")
    print("-" * 45)
    
    for neg in sorted(neg_analysis.keys()):
        best_for_neg = max(neg_analysis[neg], key=lambda x: x['sharpe'])
        print(f"    {neg:4.1f}   |   {best_for_neg['high_threshold']:4.1f}  |  {best_for_neg['sharpe']:4.2f} |      {best_for_neg['rebalance_count']}")
    
    # 分析最优正阈值
    pos_analysis = {}
    for r in results:
        pos = r['high_threshold']
        if pos not in pos_analysis:
            pos_analysis[pos] = []
        pos_analysis[pos].append(r)
    
    print(f"\nBest negative threshold for each positive threshold:")
    print("Pos_Thresh | Best_Neg | Sharpe | Rebal_Count")
    print("-" * 45)
    
    for pos in sorted(pos_analysis.keys()):
        best_for_pos = max(pos_analysis[pos], key=lambda x: x['sharpe'])
        print(f"    {pos:4.1f}   |   {best_for_pos['low_threshold']:4.1f}  |  {best_for_pos['sharpe']:4.2f} |      {best_for_pos['rebalance_count']}")
    
    return results

if __name__ == "__main__":
    results = test_key_combinations()