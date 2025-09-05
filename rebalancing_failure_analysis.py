# rebalancing_failure_analysis.py
# 深度分析为什么调仓策略跑输买入持有

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi, apply_real_yield_tilt, pick_weights

def detailed_rebalancing_impact_analysis():
    """详细分析调仓对收益的具体影响"""
    print("=== Why Rebalancing Strategy Underperformed ===\n")
    
    # 获取数据
    price_w, mhi, ry_w = build_mhi()
    
    # 模拟买入持有策略 (基础权重，无调仓)
    buy_hold_returns = []
    for i in range(1, len(price_w)):
        spy_ret = price_w['SPY'].iloc[i] / price_w['SPY'].iloc[i-1] - 1
        gld_ret = price_w['GLD'].iloc[i] / price_w['GLD'].iloc[i-1] - 1
        btc_ret = price_w['BTC'].iloc[i] / price_w['BTC'].iloc[i-1] - 1
        
        # 基础权重: SPY 35%, GLD 45%, BTC 10%, CASH 10%
        portfolio_ret = 0.35 * spy_ret + 0.45 * gld_ret + 0.10 * btc_ret
        buy_hold_returns.append(portfolio_ret)
    
    # 模拟调仓策略
    current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
    rebal_returns = []
    rebalance_events = []
    
    for i in range(1, len(price_w)):
        date = price_w.index[i]
        
        spy_ret = price_w['SPY'].iloc[i] / price_w['SPY'].iloc[i-1] - 1
        gld_ret = price_w['GLD'].iloc[i] / price_w['GLD'].iloc[i-1] - 1
        btc_ret = price_w['BTC'].iloc[i] / price_w['BTC'].iloc[i-1] - 1
        
        # 当期收益（使用当前权重）
        portfolio_ret = (current_weights["SPY"] * spy_ret + 
                        current_weights["GLD"] * gld_ret + 
                        current_weights["BTC"] * btc_ret)
        
        # 每4周检查调仓
        if i % 4 == 0 and i < len(mhi) and i >= 12:
            mhi_val = float(mhi.iloc[i])
            bucket, target = pick_weights(mhi_val)
            target = apply_real_yield_tilt(target, ry_w, date)
            
            # 三周确认机制
            recent_buckets = []
            for j in range(1, 4):
                if i-j*4 >= 0 and i-j*4 < len(mhi):
                    recent_bucket, _ = pick_weights(float(mhi.iloc[i-j*4]))
                    recent_buckets.append(recent_bucket)
            
            if len(set(recent_buckets)) == 1 and bucket != "NEUTRAL":
                # 记录调仓事件
                old_weights = current_weights.copy()
                
                # 计算交易成本并扣除
                trading_cost = calculate_trading_cost(old_weights, target)
                portfolio_ret -= trading_cost
                
                rebalance_events.append({
                    'date': date,
                    'week_index': i,
                    'mhi': mhi_val,
                    'bucket': bucket,
                    'old_weights': old_weights,
                    'new_weights': target,
                    'trading_cost': trading_cost,
                    'spy_ret': spy_ret,
                    'gld_ret': gld_ret,
                    'btc_ret': btc_ret
                })
                
                current_weights = target.copy()
        
        rebal_returns.append(portfolio_ret)
    
    # 转换为Series
    buy_hold_series = pd.Series(buy_hold_returns, index=price_w.index[1:])
    rebal_series = pd.Series(rebal_returns, index=price_w.index[1:])
    
    # 累积收益
    buy_hold_cumret = (1 + buy_hold_series).cumprod()
    rebal_cumret = (1 + rebal_series).cumprod()
    
    print("=== OVERALL PERFORMANCE COMPARISON ===")
    print(f"Buy & Hold Final Return: {buy_hold_cumret.iloc[-1] - 1:.1%}")
    print(f"Rebalancing Final Return: {rebal_cumret.iloc[-1] - 1:.1%}")
    print(f"Difference: {(rebal_cumret.iloc[-1] - buy_hold_cumret.iloc[-1]):.1%}")
    print(f"Number of Rebalancing Events: {len(rebalance_events)}")
    print()
    
    # 详细分析每次调仓的影响
    print("=== DETAILED REBALANCING IMPACT ANALYSIS ===\n")
    
    total_trading_costs = 0
    total_timing_loss = 0
    
    for i, event in enumerate(rebalance_events, 1):
        print(f"--- Rebalancing Event {i} ---")
        print(f"Date: {event['date'].strftime('%Y-%m-%d')}")
        print(f"Week Index: {event['week_index']}")
        print(f"MHI Value: {event['mhi']:.2f} ({event['bucket']})")
        print(f"Trading Cost: {event['trading_cost']:.2%}")
        
        print(f"\nWeight Changes:")
        for asset in ['SPY', 'GLD', 'BTC', 'CASH']:
            old_w = event['old_weights'][asset]
            new_w = event['new_weights'][asset]
            change = new_w - old_w
            print(f"  {asset}: {old_w:.1%} -> {new_w:.1%} ({change:+.1%})")
        
        print(f"\nAsset Returns This Week:")
        print(f"  SPY: {event['spy_ret']:+.1%}")
        print(f"  GLD: {event['gld_ret']:+.1%}")
        print(f"  BTC: {event['btc_ret']:+.1%}")
        
        # 计算如果不调仓vs调仓的收益差异（当周）
        old_ret = (event['old_weights']['SPY'] * event['spy_ret'] + 
                  event['old_weights']['GLD'] * event['gld_ret'] + 
                  event['old_weights']['BTC'] * event['btc_ret'])
        
        new_ret = (event['new_weights']['SPY'] * event['spy_ret'] + 
                  event['new_weights']['GLD'] * event['gld_ret'] + 
                  event['new_weights']['BTC'] * event['btc_ret'])
        
        immediate_impact = new_ret - old_ret - event['trading_cost']
        
        print(f"\nImmediate Impact Analysis:")
        print(f"  If no rebalancing: {old_ret:+.1%}")
        print(f"  After rebalancing: {new_ret:+.1%}")
        print(f"  Trading cost: {event['trading_cost']:.2%}")
        print(f"  Net impact: {immediate_impact:+.2%}")
        
        # 分析后续12周的表现
        start_idx = event['week_index']
        end_idx = min(start_idx + 12, len(price_w) - 1)
        
        if end_idx > start_idx:
            print(f"\nNext 12 Weeks Performance:")
            
            # 新权重表现
            new_weight_rets = []
            old_weight_rets = []
            
            for j in range(start_idx + 1, end_idx + 1):
                if j < len(price_w):
                    spy_ret_j = price_w['SPY'].iloc[j] / price_w['SPY'].iloc[j-1] - 1
                    gld_ret_j = price_w['GLD'].iloc[j] / price_w['GLD'].iloc[j-1] - 1
                    btc_ret_j = price_w['BTC'].iloc[j] / price_w['BTC'].iloc[j-1] - 1
                    
                    new_ret_j = (event['new_weights']['SPY'] * spy_ret_j + 
                               event['new_weights']['GLD'] * gld_ret_j + 
                               event['new_weights']['BTC'] * btc_ret_j)
                    
                    old_ret_j = (event['old_weights']['SPY'] * spy_ret_j + 
                               event['old_weights']['GLD'] * gld_ret_j + 
                               event['old_weights']['BTC'] * btc_ret_j)
                    
                    new_weight_rets.append(new_ret_j)
                    old_weight_rets.append(old_ret_j)
            
            if new_weight_rets:
                new_weight_cumret = np.prod([1 + r for r in new_weight_rets]) - 1
                old_weight_cumret = np.prod([1 + r for r in old_weight_rets]) - 1
                timing_effect = new_weight_cumret - old_weight_cumret
                
                print(f"  New weights performance: {new_weight_cumret:+.1%}")
                print(f"  Old weights performance: {old_weight_cumret:+.1%}")
                print(f"  Timing effect: {timing_effect:+.1%}")
                
                total_timing_loss += timing_effect
        
        total_trading_costs += event['trading_cost']
        print("\n" + "="*60)
        print()
    
    print("=== SUMMARY OF UNDERPERFORMANCE ===")
    print(f"Total Trading Costs: {total_trading_costs:.2%}")
    print(f"Total Timing Loss: {total_timing_loss:+.1%}")
    print(f"Combined Effect: {total_trading_costs + total_timing_loss:+.1%}")
    print()
    
    underperformance = (buy_hold_cumret.iloc[-1] - rebal_cumret.iloc[-1])
    print(f"Actual Underperformance: {underperformance:+.1%}")
    print()
    
    # 分析资产表现
    print("=== ASSET PERFORMANCE OVER FULL PERIOD ===")
    spy_total = price_w['SPY'].iloc[-1] / price_w['SPY'].iloc[0] - 1
    gld_total = price_w['GLD'].iloc[-1] / price_w['GLD'].iloc[0] - 1
    btc_total = price_w['BTC'].iloc[-1] / price_w['BTC'].iloc[0] - 1
    
    print(f"SPY Total Return: {spy_total:.1%}")
    print(f"GLD Total Return: {gld_total:.1%}")
    print(f"BTC Total Return: {btc_total:.1%}")
    print()
    
    print("=== WHY REBALANCING FAILED ===")
    if total_timing_loss < 0:
        print("1. BAD MARKET TIMING: Strategy reduced allocation to best-performing assets at wrong times")
    else:
        print("1. GOOD MARKET TIMING: Strategy improved allocation timing")
    
    if total_trading_costs > abs(total_timing_loss):
        print("2. TRADING COSTS: Transaction costs outweighed any timing benefits")
    
    if btc_total > max(spy_total, gld_total) and len(rebalance_events) > 0:
        print("3. MISSED BITCOIN GAINS: Strategy reduced BTC allocation during its best performance periods")
    
    print(f"\nRECOMMENDATION:")
    if underperformance > 0.02:  # 2%以上
        print("- Consider eliminating rebalancing and stick to buy & hold")
        print("- Or adjust thresholds to be even more selective")
    else:
        print("- Performance difference is small; strategy provides other benefits like risk management")
    
    return {
        'buy_hold_return': buy_hold_cumret.iloc[-1] - 1,
        'rebal_return': rebal_cumret.iloc[-1] - 1,
        'underperformance': underperformance,
        'trading_costs': total_trading_costs,
        'timing_loss': total_timing_loss,
        'rebalance_events': rebalance_events
    }

def calculate_trading_cost(old_weights, new_weights):
    """计算交易成本"""
    TOTAL_TRADING_COSTS = {
        "SPY": 0.0008, "GLD": 0.0015, "BTC": 0.0040, "CASH": 0.0000
    }
    
    total_cost = 0.0
    for asset in ["SPY", "GLD", "BTC", "CASH"]:
        weight_change = abs(new_weights.get(asset, 0.0) - old_weights.get(asset, 0.0))
        total_cost += weight_change * TOTAL_TRADING_COSTS[asset]
    
    return total_cost

if __name__ == "__main__":
    results = detailed_rebalancing_impact_analysis()