# rebalance_analysis.py
# 详细分析每次调仓的效果

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi, pick_weights, apply_real_yield_tilt

def analyze_rebalancing():
    """详细分析每次调仓的时机和效果"""
    price_w, mhi, ry_w = build_mhi()
    
    # 模拟策略，记录所有调仓细节
    current_weights = {"SPY": 0.35, "GLD": 0.45, "BTC": 0.10, "CASH": 0.10}
    rebalancing_log = []
    
    print("=== MHI Strategy Rebalancing Analysis ===\n")
    print("Initial weights:", current_weights)
    print()
    
    for i in range(12, len(price_w), 4):  # 每4周检查一次，从第12周开始
        date = price_w.index[i]
        
        if i >= len(mhi):
            continue
            
        mhi_val = float(mhi.iloc[i])
        bucket, target = pick_weights(mhi_val)
        target = apply_real_yield_tilt(target, ry_w, date)
        
        # 检查过去3次的确认
        recent_buckets = []
        for j in range(1, 4):
            if i-j*4 >= 0 and i-j*4 < len(mhi):
                recent_bucket, _ = pick_weights(float(mhi.iloc[i-j*4]))
                recent_buckets.append(recent_bucket)
        
        confirmed = len(set(recent_buckets)) == 1 if len(recent_buckets) >= 3 else False
        
        # 只在极端MHI条件下调仓
        need_rebalance = (bucket != "NEUTRAL")
        max_deviation = 0
        for k in ["SPY", "GLD", "BTC"]:
            deviation = abs(current_weights[k] - target[k])
            max_deviation = max(max_deviation, deviation)
        
        # 如果需要调仓且确认
        if need_rebalance and confirmed:
            print(f"=== REBALANCING EVENT {len(rebalancing_log)+1} ===")
            print(f"Date: {date.date()}")
            print(f"MHI Value: {mhi_val:.2f} (Bucket: {bucket})")
            print(f"Max deviation from target: {max_deviation:.1%}")
            print(f"Confirmed signal: {confirmed}")
            print()
            
            # 记录调仓前的权重
            old_weights = current_weights.copy()
            
            # 计算调仓前后一段时间的表现
            pre_period = 12  # 调仓前12周
            post_period = 12  # 调仓后12周
            
            pre_start = max(0, i - pre_period)
            post_end = min(len(price_w), i + post_period)
            
            # 调仓前表现 (用当前权重)
            pre_returns = []
            for j in range(pre_start + 1, i + 1):
                if j < len(price_w):
                    spy_ret = price_w["SPY"].iloc[j] / price_w["SPY"].iloc[j-1] - 1
                    gld_ret = price_w["GLD"].iloc[j] / price_w["GLD"].iloc[j-1] - 1
                    btc_ret = price_w["BTC"].iloc[j] / price_w["BTC"].iloc[j-1] - 1
                    portfolio_ret = (old_weights["SPY"] * spy_ret + 
                                   old_weights["GLD"] * gld_ret + 
                                   old_weights["BTC"] * btc_ret)
                    pre_returns.append(portfolio_ret)
            
            # 调仓到新权重
            current_weights = target.copy()
            
            # 调仓后表现 (用新权重)
            post_returns = []
            for j in range(i + 1, post_end):
                if j < len(price_w):
                    spy_ret = price_w["SPY"].iloc[j] / price_w["SPY"].iloc[j-1] - 1
                    gld_ret = price_w["GLD"].iloc[j] / price_w["GLD"].iloc[j-1] - 1
                    btc_ret = price_w["BTC"].iloc[j] / price_w["BTC"].iloc[j-1] - 1
                    portfolio_ret = (current_weights["SPY"] * spy_ret + 
                                   current_weights["GLD"] * gld_ret + 
                                   current_weights["BTC"] * btc_ret)
                    post_returns.append(portfolio_ret)
            
            # 如果没有调仓的假想表现
            counterfactual_returns = []
            for j in range(i + 1, post_end):
                if j < len(price_w):
                    spy_ret = price_w["SPY"].iloc[j] / price_w["SPY"].iloc[j-1] - 1
                    gld_ret = price_w["GLD"].iloc[j] / price_w["GLD"].iloc[j-1] - 1
                    btc_ret = price_w["BTC"].iloc[j] / price_w["BTC"].iloc[j-1] - 1
                    portfolio_ret = (old_weights["SPY"] * spy_ret + 
                                   old_weights["GLD"] * gld_ret + 
                                   old_weights["BTC"] * btc_ret)
                    counterfactual_returns.append(portfolio_ret)
            
            # 计算各资产在调仓后的表现
            asset_post_returns = {}
            if post_returns:
                for asset in ["SPY", "GLD", "BTC"]:
                    asset_rets = []
                    for j in range(i + 1, post_end):
                        if j < len(price_w):
                            asset_ret = price_w[asset].iloc[j] / price_w[asset].iloc[j-1] - 1
                            asset_rets.append(asset_ret)
                    if asset_rets:
                        asset_post_returns[asset] = (np.prod([1 + r for r in asset_rets]) - 1)
            
            # 结果汇总
            pre_total_ret = np.prod([1 + r for r in pre_returns]) - 1 if pre_returns else 0
            post_total_ret = np.prod([1 + r for r in post_returns]) - 1 if post_returns else 0
            counterfactual_ret = np.prod([1 + r for r in counterfactual_returns]) - 1 if counterfactual_returns else 0
            
            print("Weight Changes:")
            for asset in ["SPY", "GLD", "BTC", "CASH"]:
                change = target[asset] - old_weights[asset]
                print(f"  {asset}: {old_weights[asset]:.1%} -> {target[asset]:.1%} ({change:+.1%})")
            print()
            
            print(f"Performance Analysis ({post_period} weeks):")
            print(f"  Pre-rebalancing return ({pre_period} weeks): {pre_total_ret:.1%}")
            print(f"  Post-rebalancing return: {post_total_ret:.1%}")
            print(f"  If no rebalancing: {counterfactual_ret:.1%}")
            print(f"  Rebalancing effect: {post_total_ret - counterfactual_ret:+.1%}")
            print()
            
            print("Individual asset performance post-rebalancing:")
            for asset, ret in asset_post_returns.items():
                weight_change = target[asset] - old_weights[asset]
                print(f"  {asset}: {ret:+.1%} (weight {weight_change:+.1%})")
            print()
            
            # 保存到日志
            rebalancing_log.append({
                'date': date,
                'mhi_value': mhi_val,
                'bucket': bucket,
                'old_weights': old_weights,
                'new_weights': target,
                'pre_return': pre_total_ret,
                'post_return': post_total_ret,
                'counterfactual_return': counterfactual_ret,
                'effect': post_total_ret - counterfactual_ret,
                'asset_returns': asset_post_returns
            })
            
            print("-" * 60)
            print()
    
    # 总结
    print("=== REBALANCING SUMMARY ===")
    print(f"Total rebalancing events: {len(rebalancing_log)}")
    
    if rebalancing_log:
        total_effect = sum([log['effect'] for log in rebalancing_log])
        positive_effects = sum([1 for log in rebalancing_log if log['effect'] > 0])
        print(f"Positive rebalancing decisions: {positive_effects}/{len(rebalancing_log)}")
        print(f"Cumulative rebalancing effect: {total_effect:+.1%}")
        
        print("\nRebalancing Timeline:")
        for i, log in enumerate(rebalancing_log, 1):
            print(f"  {i}. {log['date'].date()}: MHI={log['mhi_value']:.2f}, Effect={log['effect']:+.1%}")
    
    return rebalancing_log

if __name__ == "__main__":
    analyze_rebalancing()