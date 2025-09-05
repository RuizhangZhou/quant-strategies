# btc_allocation_consensus.py
# 基于2024-2025年市场共识的比特币配置建议

def analyze_current_btc_allocation_recommendations():
    """分析当前机构和财务顾问对BTC配置的建议"""
    print("=== Current Bitcoin Allocation Recommendations (2024-2025) ===\n")
    
    # 机构建议汇总
    recommendations = [
        {
            "institution": "BlackRock",
            "allocation": "2%",
            "category": "Conservative",
            "rationale": "Optimal for typical portfolio risk management"
        },
        {
            "institution": "VanEck",
            "allocation": "6%",
            "category": "Moderate",
            "rationale": "3% BTC + 3% ETH maximizes risk-adjusted returns"
        },
        {
            "institution": "Grayscale",
            "allocation": "5%",
            "category": "Moderate",
            "rationale": "Optimizes portfolio risk-adjusted returns"
        },
        {
            "institution": "Financial Advisors",
            "allocation": "1-5%",
            "category": "Conservative",
            "rationale": "Upside capture with constrained downside risk"
        },
        {
            "institution": "Cathie Wood (ARK)",
            "allocation": "19%",
            "category": "Aggressive",
            "rationale": "High conviction in Bitcoin's long-term potential"
        },
        {
            "institution": "New Trend Advisors",
            "allocation": "10%+",
            "category": "Progressive",
            "rationale": "Longer investment horizons justify higher allocation"
        }
    ]
    
    print("Institution/Source        | Allocation | Category     | Key Rationale")
    print("-" * 80)
    
    for rec in recommendations:
        print(f"{rec['institution']:24s} | {rec['allocation']:10s} | {rec['category']:12s} | {rec['rationale']}")
    
    print(f"\n=== CONSENSUS ANALYSIS ===\n")
    
    # 按风险偏好分类
    risk_categories = {
        "Ultra-Conservative": "1-2%",
        "Conservative": "2-5%", 
        "Moderate": "5-10%",
        "Aggressive": "10-20%",
        "Speculative": "20%+"
    }
    
    print("Risk Profile        | Recommended BTC Allocation | Characteristics")
    print("-" * 70)
    print("Ultra-Conservative  |          1-2%              | Capital preservation focus")
    print("Conservative        |          2-5%              | Traditional investors")
    print("Moderate           |          5-10%             | Balanced risk/reward")
    print("Aggressive         |         10-20%             | Growth-focused")
    print("Speculative        |          20%+              | High risk tolerance")
    
    print(f"\n=== 2024-2025 MARKET REALITY CHECK ===\n")
    
    print("Key Changes from Previous Years:")
    print("✓ Institutional acceptance increasing")
    print("✓ ETF approvals providing easier access")
    print("✓ Regulatory clarity improving")
    print("✓ Bitcoin maturing as asset class")
    print("✗ Returns diminishing (no more 50x cycles expected)")
    print("✗ Volatility remains high (60%+ annually)")
    print("✗ Correlation with stocks increasing in crisis")
    print()
    
    # 基于你的情况的建议
    print("=== RECOMMENDATION FOR YOUR SITUATION ===\n")
    
    print("Based on your risk-conscious approach and current market maturity:")
    print()
    
    print("CURRENT CONSENSUS SWEET SPOT: 5-8%")
    print("- Most institutional research points to 5-6% as optimal")
    print("- Provides meaningful upside exposure")  
    print("- Limits downside risk to manageable levels")
    print("- Aligns with Bitcoin's maturation as asset class")
    print()
    
    print("YOUR STRATEGY ADJUSTMENT OPTIONS:")
    print()
    print("Option 1 - Conservative Increase (Recommended):")
    print("  • Base allocation: 8% (up from current 10%)")
    print("  • Crisis allocation: 4% (up from current 5%)")
    print("  • Rationale: Follow institutional consensus")
    print()
    
    print("Option 2 - Moderate Increase:")
    print("  • Base allocation: 12% (up from current 10%)")
    print("  • Crisis allocation: 6% (up from current 5%)")
    print("  • Rationale: Slightly above consensus for growth")
    print()
    
    print("Option 3 - Keep Current (Also Valid):")
    print("  • Base allocation: 10% (current)")
    print("  • Crisis allocation: 5% (current)")
    print("  • Rationale: Already within reasonable range")
    print()
    
    print("Option 4 - Ultra-Conservative:")
    print("  • Base allocation: 5%")
    print("  • Crisis allocation: 2%")
    print("  • Rationale: BlackRock/traditional advisor approach")
    print()
    
    # 风险收益权衡
    print("=== RISK-RETURN TRADE-OFF ANALYSIS ===\n")
    
    allocations = [2, 5, 8, 10, 15, 20]
    print("BTC %  | Expected Additional Return | Additional Risk | Risk-Adjusted Score")
    print("-" * 75)
    
    for alloc in allocations:
        # 简化的风险收益估算
        additional_return = alloc * 0.3  # 假设BTC未来年化30%
        additional_risk = alloc * 0.8    # 假设增加的组合风险
        risk_adj_score = additional_return / max(additional_risk, 1) if additional_risk > 0 else 0
        
        print(f"{alloc:4d}%  |          {additional_return:4.1f}%            |      {additional_risk:4.1f}%      |       {risk_adj_score:.2f}")
    
    print(f"\n=== FINAL RECOMMENDATION ===\n")
    
    print("🎯 OPTIMAL ALLOCATION FOR YOU: 8%")
    print()
    print("Reasons:")
    print("1. Aligns with institutional consensus (5-10% range)")
    print("2. Accounts for Bitcoin's maturation (lower future returns expected)")
    print("3. Balances growth potential with your risk preferences")
    print("4. Provides meaningful exposure without dominating portfolio")
    print("5. Reduces regret risk while maintaining stability focus")
    print()
    
    print("Implementation:")
    print("• Base Weight: SPY 32%, GLD 45%, BTC 8%, CASH 15%")
    print("• Low MHI: SPY 50%, GLD 25%, BTC 4%, CASH 21%")  
    print("• High MHI: SPY 14%, GLD 60%, BTC 4%, CASH 22%")
    print()
    
    print("This gives you:")
    print("✓ Better upside capture than current 10%→5% reduction")
    print("✓ Still conservative compared to aggressive investors (20%+)")
    print("✓ Aligned with professional asset management practices")
    print("✓ Room for growth if Bitcoin adoption continues")

if __name__ == "__main__":
    analyze_current_btc_allocation_recommendations()