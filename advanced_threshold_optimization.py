# advanced_threshold_optimization.py
# 包含交易成本的正负阈值独立优化测试

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi, apply_real_yield_tilt
import itertools

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
    
    # 现金上限保护
    target["CASH"] = min(target.get("CASH",0.0), CASH_MAX)
    # 三资产权重重新归一
    s = target["SPY"]+target["GLD"]+target["BTC"]
    if s > 0:
        scale = (1 - target["CASH"]) / s
        for k in ["SPY","GLD","BTC"]:
            target[k] = max(0.0, target[k]*scale)
    
    return bucket, target

def calculate_trading_costs(old_weights, new_weights, total_value):
    """计算交易成本"""
    # 交易成本配置
    TRANSACTION_COSTS = {
        "SPY": 0.0005,   # 0.05% (股票ETF相对便宜)
        "GLD": 0.0010,   # 0.10% (黄金ETF略贵)
        "BTC": 0.0025,   # 0.25% (加密货币滑点较大)
        "CASH": 0.0000   # 现金无成本
    }
    
    BID_ASK_SPREADS = {
        "SPY": 0.0001,   # 0.01% (流动性很好)
        "GLD": 0.0003,   # 0.03% (流动性一般)
        "BTC": 0.0015,   # 0.15% (波动大，价差大)
        "CASH": 0.0000
    }
    
    total_cost = 0.0
    
    for asset in ["SPY", "GLD", "BTC", "CASH"]:
        old_val = old_weights.get(asset, 0.0) * total_value
        new_val = new_weights.get(asset, 0.0) * total_value
        trade_amount = abs(new_val - old_val)
        
        if trade_amount > 0:
            # 交易手续费
            commission_cost = trade_amount * TRANSACTION_COSTS[asset]
            # 买卖价差成本
            spread_cost = trade_amount * BID_ASK_SPREADS[asset]
            total_cost += commission_cost + spread_cost
    
    # 返回成本占组合的比例
    return total_cost / total_value if total_value > 0 else 0.0

def simulate_strategy_with_costs(low_threshold, high_threshold):
    """包含交易成本的策略模拟"""
    price_w, mhi, ry_w = build_mhi()
    
    current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
    portfolio_value = 100000.0
    strategy_returns = []
    rebalance_count = 0
    total_trading_costs = 0.0
    rebalance_details = []
    
    for i in range(1, len(price_w)):
        date = price_w.index[i]
        
        # 计算当期资产收益
        spy_ret = price_w["SPY"].iloc[i] / price_w["SPY"].iloc[i-1] - 1
        gld_ret = price_w["GLD"].iloc[i] / price_w["GLD"].iloc[i-1] - 1 
        btc_ret = price_w["BTC"].iloc[i] / price_w["BTC"].iloc[i-1] - 1
        
        # 计算组合收益（扣除交易成本前）
        gross_portfolio_ret = (current_weights["SPY"] * spy_ret + 
                              current_weights["GLD"] * gld_ret + 
                              current_weights["BTC"] * btc_ret)
        
        # 更新组合价值
        portfolio_value *= (1 + gross_portfolio_ret)
        net_portfolio_ret = gross_portfolio_ret
        
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
                        # 计算交易成本
                        trading_cost_pct = calculate_trading_costs(current_weights, target, portfolio_value)
                        
                        # 扣除交易成本
                        portfolio_value *= (1 - trading_cost_pct)
                        net_portfolio_ret -= trading_cost_pct
                        
                        total_trading_costs += trading_cost_pct
                        
                        # 记录调仓详情
                        weight_changes = {}
                        for asset in ["SPY", "GLD", "BTC", "CASH"]:
                            weight_changes[asset] = target[asset] - current_weights.get(asset, 0.0)
                        
                        rebalance_details.append({
                            'date': date,
                            'mhi': mhi_val,
                            'bucket': bucket,
                            'trading_cost_pct': trading_cost_pct,
                            'weight_changes': weight_changes
                        })
                        
                        # 更新权重
                        current_weights = target.copy()
                        rebalance_count += 1
        
        strategy_returns.append(net_portfolio_ret)
    
    return (pd.Series(strategy_returns, index=price_w.index[1:]), 
            rebalance_count, total_trading_costs, rebalance_details)

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

def comprehensive_threshold_test():
    """全面的正负阈值独立测试"""
    print("=== Advanced MHI Threshold Optimization (With Trading Costs) ===\n")
    
    # 设定测试范围
    negative_thresholds = [-1.2, -1.3, -1.4, -1.5, -1.6, -1.7, -1.8, -1.9, -2.0, -2.1, -2.2]
    positive_thresholds = [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2]
    
    print(f"Testing {len(negative_thresholds)}×{len(positive_thresholds)} = {len(negative_thresholds)*len(positive_thresholds)} combinations...")
    print()
    
    all_results = []
    best_sharpe = -999
    best_return = -999
    best_sharpe_combo = None
    best_return_combo = None
    
    print("Progress: ", end="", flush=True)
    total_tests = len(negative_thresholds) * len(positive_thresholds)
    completed = 0
    
    for neg_thresh in negative_thresholds:
        for pos_thresh in positive_thresholds:
            completed += 1
            if completed % 10 == 0:
                print(f"{completed}/{total_tests}", end=" ", flush=True)
            
            strategy_returns, rebal_count, total_costs, rebal_details = simulate_strategy_with_costs(neg_thresh, pos_thresh)
            metrics = calculate_metrics(strategy_returns)
            
            result = {
                'low_threshold': neg_thresh,
                'high_threshold': pos_thresh,
                'rebalance_count': rebal_count,
                'total_trading_costs': total_costs,
                'rebalance_details': rebal_details,
                **metrics
            }
            
            all_results.append(result)
            
            # 追踪最佳组合
            if metrics['sharpe'] > best_sharpe:
                best_sharpe = metrics['sharpe']
                best_sharpe_combo = (neg_thresh, pos_thresh)
            
            if metrics['total_return'] > best_return:
                best_return = metrics['total_return']
                best_return_combo = (neg_thresh, pos_thresh)
    
    print(f"\nCompleted {total_tests} tests!\n")
    
    # 按夏普比率排序找出最佳组合
    sorted_by_sharpe = sorted(all_results, key=lambda x: x['sharpe'], reverse=True)
    sorted_by_return = sorted(all_results, key=lambda x: x['total_return'], reverse=True)
    
    print("=== TOP 10 COMBINATIONS BY SHARPE RATIO ===")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count | Trading_Costs")
    print("-" * 100)
    
    for i, result in enumerate(sorted_by_sharpe[:10]):
        print(f"    {result['low_threshold']:4.1f}   |     {result['high_threshold']:4.1f}    |   {result['total_return']:5.1%}   |    {result['annual_return']:5.1%}   |  {result['sharpe']:4.2f}  | {result['max_dd']:5.1%}  |      {result['rebalance_count']}      |    {result['total_trading_costs']:5.2%}")
    
    print(f"\n=== TOP 10 COMBINATIONS BY TOTAL RETURN ===")
    print("Low_Thresh | High_Thresh | Total_Ret | Annual_Ret | Sharpe | Max_DD | Rebal_Count | Trading_Costs")
    print("-" * 100)
    
    for i, result in enumerate(sorted_by_return[:10]):
        print(f"    {result['low_threshold']:4.1f}   |     {result['high_threshold']:4.1f}    |   {result['total_return']:5.1%}   |    {result['annual_return']:5.1%}   |  {result['sharpe']:4.2f}  | {result['max_dd']:5.1%}  |      {result['rebalance_count']}      |    {result['total_trading_costs']:5.2%}")
    
    # 分析最优阈值的临界点效应
    print(f"\n=== THRESHOLD SENSITIVITY ANALYSIS ===\n")
    
    # 对于最佳夏普比率组合，分析其周围的表现
    best_combo = sorted_by_sharpe[0]
    print(f"Best Sharpe Combo: ({best_combo['low_threshold']}, {best_combo['high_threshold']}) - Sharpe: {best_combo['sharpe']:.3f}")
    
    # 分析每个负阈值的最佳表现
    print(f"\n--- Best Positive Threshold for Each Negative Threshold ---")
    print("Neg_Thresh | Best_Pos_Thresh | Sharpe | Total_Ret | Rebal_Count")
    print("-" * 65)
    
    for neg_thresh in negative_thresholds:
        neg_results = [r for r in all_results if r['low_threshold'] == neg_thresh]
        best_for_neg = max(neg_results, key=lambda x: x['sharpe'])
        print(f"    {neg_thresh:4.1f}   |      {best_for_neg['high_threshold']:4.1f}      |  {best_for_neg['sharpe']:4.2f} |   {best_for_neg['total_return']:5.1%}   |      {best_for_neg['rebalance_count']}")
    
    # 分析每个正阈值的最佳表现
    print(f"\n--- Best Negative Threshold for Each Positive Threshold ---")
    print("Pos_Thresh | Best_Neg_Thresh | Sharpe | Total_Ret | Rebal_Count")
    print("-" * 65)
    
    for pos_thresh in positive_thresholds:
        pos_results = [r for r in all_results if r['high_threshold'] == pos_thresh]
        best_for_pos = max(pos_results, key=lambda x: x['sharpe'])
        print(f"    {pos_thresh:4.1f}   |      {best_for_pos['low_threshold']:4.1f}      |  {best_for_pos['sharpe']:4.2f} |   {best_for_pos['total_return']:5.1%}   |      {best_for_pos['rebalance_count']}")
    
    # 按调仓次数分析
    print(f"\n=== PERFORMANCE BY REBALANCING FREQUENCY ===\n")
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
        avg_costs = np.mean([r['total_trading_costs'] for r in group])
        best_in_group = max(group, key=lambda x: x['sharpe'])
        
        print(f"Rebalance Count {count}: {len(group):2d} combinations")
        print(f"  Avg Sharpe: {avg_sharpe:.3f}, Avg Return: {avg_return:5.1%}, Avg Trading Costs: {avg_costs:5.2%}")
        print(f"  Best in group: ({best_in_group['low_threshold']:.1f}, {best_in_group['high_threshold']:.1f}) - Sharpe: {best_in_group['sharpe']:.3f}")
        print()
    
    # 详细分析最佳组合的调仓情况
    print(f"=== DETAILED ANALYSIS OF BEST COMBINATION ===\n")
    best = sorted_by_sharpe[0]
    print(f"Optimal Thresholds: Low = {best['low_threshold']:.1f}, High = {best['high_threshold']:.1f}")
    print(f"Performance: Sharpe = {best['sharpe']:.3f}, Total Return = {best['total_return']:.1%}")
    print(f"Risk: Max Drawdown = {best['max_dd']:.1%}, Annual Vol = {best['annual_vol']:.1%}")
    print(f"Trading: {best['rebalance_count']} rebalances, {best['total_trading_costs']:.2%} total costs")
    print()
    
    if best['rebalance_details']:
        print("Rebalancing Events:")
        print("Date       | MHI   | Bucket | Trading Cost | Weight Changes")
        print("-" * 60)
        for detail in best['rebalance_details']:
            changes_str = ", ".join([f"{k}:{v:+.1%}" for k, v in detail['weight_changes'].items() if abs(v) > 0.001])
            print(f"{detail['date'].strftime('%Y-%m-%d')} | {detail['mhi']:5.2f} | {detail['bucket']:6s} |    {detail['trading_cost_pct']:5.2%}    | {changes_str}")
    
    return all_results, sorted_by_sharpe[0]

if __name__ == "__main__":
    results, best_combo = comprehensive_threshold_test()