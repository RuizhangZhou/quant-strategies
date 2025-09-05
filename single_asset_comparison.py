# single_asset_comparison.py
# 对比策略与单一资产持有的表现

import pandas as pd
import numpy as np
from mhi_weekly import build_mhi

def calculate_asset_metrics(price_series, asset_name):
    """计算单一资产的收益指标"""
    returns = price_series.pct_change().fillna(0)
    
    # 去掉第一个NaN值
    returns = returns.dropna()
    
    # 累积收益
    cumulative_returns = (1 + returns).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1
    
    # 年化收益率 (周频数据)
    years = len(returns) / 52
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
    
    # 年化波动率
    annual_vol = returns.std() * np.sqrt(52)
    
    # 夏普比率
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # 最大回撤
    max_dd = (cumulative_returns / cumulative_returns.cummax() - 1).min()
    
    # 计算年度收益率
    yearly_returns = []
    price_data = price_series.dropna()
    start_year = price_data.index[0].year
    end_year = price_data.index[-1].year
    
    for year in range(start_year + 1, end_year + 1):
        year_start = price_data[price_data.index.year == year-1].iloc[-1] if len(price_data[price_data.index.year == year-1]) > 0 else None
        year_end = price_data[price_data.index.year == year].iloc[-1] if len(price_data[price_data.index.year == year]) > 0 else None
        
        if year_start is not None and year_end is not None:
            year_return = (year_end / year_start) - 1
            yearly_returns.append(year_return)
    
    return {
        'asset': asset_name,
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_vol': annual_vol,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'yearly_returns': yearly_returns,
        'years': years
    }

def compare_with_single_assets():
    """对比策略与单一资产表现"""
    print("=== Strategy vs Single Asset Comparison (2015-2025) ===\n")
    
    # 获取价格数据
    price_w, mhi, ry_w = build_mhi()
    
    # 计算各资产表现
    assets_performance = {}
    
    # SPY
    assets_performance['SPY'] = calculate_asset_metrics(price_w['SPY'], 'SPY (S&P 500)')
    
    # GLD  
    assets_performance['GLD'] = calculate_asset_metrics(price_w['GLD'], 'GLD (Gold)')
    
    # BTC
    assets_performance['BTC'] = calculate_asset_metrics(price_w['BTC'], 'BTC (Bitcoin)')
    
    # 我们的策略结果(从之前测试得出)
    strategy_result = {
        'asset': 'MHI Strategy',
        'total_return': 1.449,  # 144.9%
        'annual_return': 0.169,  # 16.9%
        'annual_vol': 0.146,    # 14.6%
        'sharpe': 1.21,
        'max_dd': -0.214,       # -21.4%
        'years': 10
    }
    
    print("=== 10-Year Performance Comparison ===")
    print("Asset              | Total Return | Annual Return | Annual Vol | Sharpe | Max Drawdown")
    print("-" * 90)
    
    all_results = [strategy_result]
    for asset, perf in assets_performance.items():
        all_results.append(perf)
        
    for result in all_results:
        print(f"{result['asset']:18s} |    {result['total_return']:6.1%}    |     {result['annual_return']:5.1%}     |   {result['annual_vol']:5.1%}    |  {result['sharpe']:4.2f}  |    {result['max_dd']:5.1%}")
    
    print(f"\n=== Risk-Adjusted Performance Analysis ===\n")
    
    # 按夏普比率排序
    sorted_by_sharpe = sorted(all_results, key=lambda x: x['sharpe'], reverse=True)
    print("Ranking by Sharpe Ratio:")
    for i, result in enumerate(sorted_by_sharpe, 1):
        print(f"{i}. {result['asset']:18s}: {result['sharpe']:4.2f}")
    
    print(f"\nRanking by Total Return:")
    sorted_by_return = sorted(all_results, key=lambda x: x['total_return'], reverse=True)
    for i, result in enumerate(sorted_by_return, 1):
        print(f"{i}. {result['asset']:18s}: {result['total_return']:6.1%}")
    
    print(f"\n=== Detailed Analysis ===\n")
    
    # 详细分析每个资产
    for asset, perf in assets_performance.items():
        print(f"--- {perf['asset']} ---")
        print(f"  Investment period: {perf['years']:.1f} years")
        print(f"  Total return: {perf['total_return']:.1%}")
        print(f"  Annual return: {perf['annual_return']:.1%}")
        print(f"  Annual volatility: {perf['annual_vol']:.1%}")
        print(f"  Sharpe ratio: {perf['sharpe']:.2f}")
        print(f"  Max drawdown: {perf['max_dd']:.1%}")
        
        if perf['yearly_returns']:
            positive_years = sum(1 for r in perf['yearly_returns'] if r > 0)
            total_years = len(perf['yearly_returns'])
            print(f"  Positive years: {positive_years}/{total_years} ({positive_years/total_years:.0%})")
            print(f"  Annual return range: {min(perf['yearly_returns']):.1%} ~ {max(perf['yearly_returns']):.1%}")
        print()
    
    print(f"--- MHI Strategy ---")
    print(f"  Investment period: 10.0 years")
    print(f"  Total return: {strategy_result['total_return']:.1%}")
    print(f"  Annual return: {strategy_result['annual_return']:.1%}")
    print(f"  Annual volatility: {strategy_result['annual_vol']:.1%}")
    print(f"  Sharpe ratio: {strategy_result['sharpe']:.2f}")
    print(f"  Max drawdown: {strategy_result['max_dd']:.1%}")
    print(f"  Rebalancing count: 2 times (ultra-low frequency)")
    print(f"  Trading costs: 0.07%")
    print()
    
    print(f"=== Strategy Performance Analysis ===\n")
    
    # 对比策略与最佳单一资产
    best_single_asset = max(assets_performance.values(), key=lambda x: x['sharpe'])
    
    print(f"Best single asset (by Sharpe): {best_single_asset['asset']}")
    print(f"  Sharpe ratio: {best_single_asset['sharpe']:.2f} vs Strategy {strategy_result['sharpe']:.2f}")
    print(f"  Annual return: {best_single_asset['annual_return']:.1%} vs Strategy {strategy_result['annual_return']:.1%}")
    print(f"  Max drawdown: {best_single_asset['max_dd']:.1%} vs Strategy {strategy_result['max_dd']:.1%}")
    print()
    
    # 总结
    print(f"=== Summary ===\n")
    
    strategy_rank_sharpe = next(i for i, r in enumerate(sorted_by_sharpe, 1) if r['asset'] == 'MHI Strategy')
    strategy_rank_return = next(i for i, r in enumerate(sorted_by_return, 1) if r['asset'] == 'MHI Strategy')
    
    print(f"MHI Strategy Performance:")
    print(f"  Sharpe ratio ranking: {strategy_rank_sharpe}/4")
    print(f"  Total return ranking: {strategy_rank_return}/4")
    print()
    
    if strategy_rank_sharpe == 1:
        print("Strategy achieves best risk-adjusted returns!")
    else:
        print(f"Strategy ranks #{strategy_rank_sharpe} in Sharpe ratio, room for improvement")
    
    # 计算如果直接买入持有基础权重组合的表现
    print(f"\n=== Base Weight Buy & Hold Comparison ===")
    
    # 基础权重: SPY 35%, GLD 45%, BTC 10%, CASH 10%
    base_weight_returns = []
    for i in range(1, len(price_w)):
        spy_ret = price_w['SPY'].iloc[i] / price_w['SPY'].iloc[i-1] - 1
        gld_ret = price_w['GLD'].iloc[i] / price_w['GLD'].iloc[i-1] - 1
        btc_ret = price_w['BTC'].iloc[i] / price_w['BTC'].iloc[i-1] - 1
        
        portfolio_ret = 0.35 * spy_ret + 0.45 * gld_ret + 0.10 * btc_ret
        # 10%现金收益为0
        base_weight_returns.append(portfolio_ret)
    
    base_weight_series = pd.Series(base_weight_returns, index=price_w.index[1:])
    base_weight_perf = calculate_asset_metrics(pd.Series((1 + base_weight_series).cumprod(), index=base_weight_series.index), 'Base Weight Buy&Hold')
    
    print(f"Base Weight Buy & Hold:")
    print(f"  Total return: {base_weight_perf['total_return']:.1%}")
    print(f"  Annual return: {base_weight_perf['annual_return']:.1%}")
    print(f"  Sharpe ratio: {base_weight_perf['sharpe']:.2f}")
    print(f"  Max drawdown: {base_weight_perf['max_dd']:.1%}")
    print()
    
    alpha = strategy_result['annual_return'] - base_weight_perf['annual_return']
    print(f"MHI Strategy vs Base Weight Buy & Hold:")
    print(f"  Alpha (excess annual return): {alpha:+.1%}")
    print(f"  Sharpe ratio improvement: {strategy_result['sharpe'] - base_weight_perf['sharpe']:+.2f}")
    
    if alpha > 0:
        print(f"Strategy successfully generates positive Alpha!")
    else:
        print(f"Strategy fails to beat buy & hold")

if __name__ == "__main__":
    compare_with_single_assets()