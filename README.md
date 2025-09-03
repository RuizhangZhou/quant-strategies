# Quantitative Trading Strategies

A collection of quantitative investment strategies for systematic portfolio management.

## Current Strategies

### 1. Market Health Indicator (MHI) Weekly Strategy

A conservative weekly rebalancing strategy that uses market sentiment indicators to adjust portfolio allocation across SPY, GLD, and BTC.

**Key Features:**
- **Market Sentiment Analysis**: Uses VIX fear index and sector breadth
- **Macro Economic Integration**: Optional FRED API integration for real yield analysis  
- **Risk Management**: Two-week confirmation mechanism and position sizing limits
- **Multi-Asset Support**: Stocks (SPY), Gold (GLD), Bitcoin (BTC)
- **Backtesting**: Built-in performance analysis with Sharpe ratio and drawdown metrics

**Usage:**
```bash
# Get current week's buy/sell recommendations
python mhi_weekly.py advise 0.4 0.4 0.2

# Run historical backtest
python mhi_weekly.py backtest
```

## Installation

1. Create conda environment:
```bash
conda create -n quant-strategies python -y
conda activate quant-strategies
```

2. Install dependencies:
```bash
pip install -U yfinance pandas numpy backtrader requests-cache python-dotenv
pip install fredapi  # Optional for FRED data
```

3. Set up environment variables:
```bash
# Create .env file with your FRED API key (optional)
echo "FRED_API_KEY=your_key_here" > .env
```

## Configuration

The MHI strategy can be customized by modifying parameters in `mhi_weekly.py`:
- `BASE_WEIGHTS`: Neutral market allocation
- `LOW_MHI_WEI`: Conservative allocation for low market health  
- `HIGH_MHI_WEI`: Defensive allocation for high market health
- `MIN_CHANGE`: Minimum threshold for rebalancing (default 3%)

## Roadmap

- [ ] Additional momentum strategies
- [ ] Volatility targeting
- [ ] Multi-timeframe analysis
- [ ] Enhanced risk metrics
- [ ] Portfolio optimization algorithms

## Disclaimer

This software is for educational and research purposes only. Not financial advice.