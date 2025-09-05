# threshold_optimization.py
# 系统性测试不同MHI阈值组合的效果

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi, apply_real_yield_tilt
import itertools

def pick_weights_custom(mhi_val, low_threshold, high_threshold):
    """自定义阈值的权重选择函数"""
    BASE_WEIGHTS = {"SPY":0.35, "GLD":0.45, "BTC":0.10, "CASH":0.10}
    LOW_MHI_WEI = {"SPY":0.55, "GLD":0.25, "BTC":0.05, "CASH":0.15}  
    HIGH_MHI_WEI = {"SPY":0.15, "GLD":0.60, "BTC":0.05, "CASH":0.20}
    CASH_MAX = 0.35
    
    if mhi_val <= low_threshold:
        bucket, target = "LOW", LOW_MHI_WEI.copy()
    elif mhi_val >= high_threshold:
        bucket, target = "HIGH", HIGH_MHI_WEI.copy()
    else:
        bucket, target = "NEUTRAL", BASE_WEIGHTS.copy()
    
    # 现金上限保护
    target["CASH"] = min(target.get("CASH",0.0), CASH_MAX)
    # 三资产权重重新归一
    s = target["SPY"]+target["GLD"]+target["BTC"]
    if s > 0:
        scale = (1 - target["CASH"]) / s
        for k in ["SPY","GLD","BTC"]:
            target[k] = max(0.0, target[k]*scale)
    
    return bucket, target

def simulate_strategy_with_thresholds(low_threshold, high_threshold):
    """使用自定义阈值模拟策略"""
    price_w, mhi, ry_w = build_mhi()
    
    current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
    strategy_returns = []
    rebalance_count = 0
    
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
        
        # 检查是否需要调仓（每4周检查一次）
        if i % 4 == 0 and i < len(mhi):
            mhi_val = float(mhi.iloc[i])
            bucket, target = pick_weights_custom(mhi_val, low_threshold, high_threshold)
            target = apply_real_yield_tilt(target, ry_w, date)
            
            # 检查确认机制（3周确认）
            if i >= 12:  # 至少3个月数据
                recent_buckets = []
                for j in range(1, 4):
                    if i-j*4 >= 0 and i-j*4 < len(mhi):
                        recent_bucket, _ = pick_weights_custom(float(mhi.iloc[i-j*4]), low_threshold, high_threshold)
                        recent_buckets.append(recent_bucket)
                
                if len(set(recent_buckets)) == 1:  # 确认信号
                    # 只在极端MHI条件下调仓
                    need_rebalance = (bucket != "NEUTRAL")
                    
                    if need_rebalance:
                        current_weights = target.copy()
                        rebalance_count += 1
    
    return pd.Series(strategy_returns, index=price_w.index[1:]), rebalance_count

def calculate_metrics(returns):
    """计算关键指标"""
    cumulative_returns = (1 + returns).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1
    
    years = len(returns) / 52
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
    annual_vol = returns.std() * np.sqrt(52)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    max_dd = (cumulative_returns / cumulative_returns.cummax() - 1).min()
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_vol': annual_vol,
        'sharpe': sharpe,
        'max_dd': max_dd
    }

def test_threshold_combinations():
    """测试不同阈值组合"""
    print("=== MHI Threshold Optimization Test ===\n")
    
    # 测试对称阈值
    symmetric_thresholds = [1.5, 1.6, 1.7, 1.75, 1.8, 1.9, 2.0]
    symmetric_results = []
    
    print("Testing Symmetric Thresholds:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count")
    print("-" * 80)
    
    for threshold in symmetric_thresholds:
        low_thresh = -threshold
        high_thresh = threshold
        
        strategy_returns, rebal_count = simulate_strategy_with_thresholds(low_thresh, high_thresh)
        metrics = calculate_metrics(strategy_returns)
        
        result = {
            'low_threshold': low_thresh,
            'high_threshold': high_thresh,
            'rebalance_count': rebal_count,
            **metrics
        }
        symmetric_results.append(result)
        
        print(f"    {low_thresh:4.2f}   |     {high_thresh:4.2f}    |   {metrics['total_return']:5.1%}   |    {metrics['annual_return']:5.1%}   |  {metrics['sharpe']:4.2f}  | {metrics['max_dd']:5.1%}  |      {rebal_count}")
    
    # 测试不对称阈值组合
    print(f"\n\nTesting Asymmetric Thresholds:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count")
    print("-" * 80)
    
    asymmetric_results = []
    
    # 测试一些有趣的不对称组合
    asymmetric_combinations = [
        (-1.5, 1.8),  # 更容易进入防守模式
        (-1.8, 1.5),  # 更容易进入进攻模式  
        (-1.6, 1.9),
        (-1.9, 1.6),
        (-1.5, 2.0),
        (-2.0, 1.5),
        (-1.7, 1.8),
        (-1.8, 1.7),
    ]
    
    for low_thresh, high_thresh in asymmetric_combinations:
        strategy_returns, rebal_count = simulate_strategy_with_thresholds(low_thresh, high_thresh)
        metrics = calculate_metrics(strategy_returns)
        
        result = {
            'low_threshold': low_thresh,
            'high_threshold': high_thresh,
            'rebalance_count': rebal_count,
            **metrics
        }
        asymmetric_results.append(result)
        
        print(f"    {low_thresh:4.2f}   |     {high_thresh:4.2f}    |   {metrics['total_return']:5.1%}   |    {metrics['annual_return']:5.1%}   |  {metrics['sharpe']:4.2f}  | {metrics['max_dd']:5.1%}  |      {rebal_count}")
    
    # 找出最优组合
    all_results = symmetric_results + asymmetric_results
    
    print(f"\n\n=== TOP PERFORMERS ===\n")
    
    # 按夏普比率排序
    best_sharpe = sorted(all_results, key=lambda x: x['sharpe'], reverse=True)[:5]
    print("Top 5 by Sharpe Ratio:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count")
    print("-" * 80)
    for result in best_sharpe:
        print(f"    {result['low_threshold']:4.2f}   |     {result['high_threshold']:4.2f}    |   {result['total_return']:5.1%}   |    {result['annual_return']:5.1%}   |  {result['sharpe']:4.2f}  | {result['max_dd']:5.1%}  |      {result['rebalance_count']}")
    
    # 按总收益排序
    best_return = sorted(all_results, key=lambda x: x['total_return'], reverse=True)[:5]
    print(f"\nTop 5 by Total Return:")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count")
    print("-" * 80)
    for result in best_return:
        print(f"    {result['low_threshold']:4.2f}   |     {result['high_threshold']:4.2f}    |   {result['total_return']:5.1%}   |    {result['annual_return']:5.1%}   |  {result['sharpe']:4.2f}  | {result['max_dd']:5.1%}  |      {result['rebalance_count']}")
    
    # 按调仓次数分组分析
    print(f"\n=== ANALYSIS BY REBALANCING FREQUENCY ===\n")
    rebal_groups = {}
    for result in all_results:
        count = result['rebalance_count']
        if count not in rebal_groups:
            rebal_groups[count] = []
        rebal_groups[count].append(result)
    
    for count in sorted(rebal_groups.keys()):
        group = rebal_groups[count]
        avg_sharpe = np.mean([r['sharpe'] for r in group])
        avg_return = np.mean([r['total_return'] for r in group])
        print(f"Rebalance Count {count}: {len(group)} combinations, Avg Sharpe: {avg_sharpe:.2f}, Avg Return: {avg_return:.1%}")
        
        # 显示这个组别中的最佳组合
        best_in_group = max(group, key=lambda x: x['sharpe'])
        print(f"  Best in group: ({best_in_group['low_threshold']:.2f}, {best_in_group['high_threshold']:.2f}) - Sharpe: {best_in_group['sharpe']:.2f}")
        print()
    
    return all_results

if __name__ == "__main__":
    results = test_threshold_combinations()