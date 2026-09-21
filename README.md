# Helios ML Trading System

## Overview

**Helios** is a comprehensive, self-learning machine learning trading Expert Advisor (EA) that integrates advanced AI capabilities with MetaTrader 5 for automated trading. The system features multi-strategy selection, chart pattern analysis, and real-time adaptation to market conditions.

![Helios ML Trading System](docs/images/helios-banner.png)

## Features

### 🤖 **Machine Learning Integration**
- **Multiple ML Models**: Random Forest, LightGBM, XGBoost, and LSTM networks
- **Ensemble Learning**: Combines predictions from multiple models for higher accuracy
- **Real-time Feature Engineering**: 100+ technical indicators and pattern recognition
- **Automated Model Training**: Self-retraining based on market data

### 📊 **Multi-Strategy Trading**
- **Trend Following**: EMA crossover with RSI confirmation
- **Mean Reversion**: Bollinger Bands with RSI oversold/overbought signals
- **Breakout Strategy**: Price momentum with volume confirmation
- **Scalping**: High-frequency trading with tight risk management

### 🧠 **Meta-Learning Engine**
- **Market Regime Detection**: Automatically identifies trending, sideways, and volatile markets
- **Dynamic Strategy Selection**: Chooses optimal strategy based on current market conditions
- **Performance Tracking**: Continuous monitoring and adaptation of strategy weights
- **Time-Based Analysis**: Session-aware trading with London, New York, and Asian market focus

### 🛡️ **Advanced Risk Management**
- **Position Sizing**: Kelly Criterion and volatility-based sizing
- **Stop Loss/Take Profit**: ATR-based dynamic levels
- **Drawdown Protection**: Maximum daily loss and portfolio heat limits
- **Risk/Reward Optimization**: Automatic risk-reward ratio management

### 🔗 **MT5 Integration**
- **Real-time Communication**: WebSocket-based two-way communication
- **Live Order Execution**: Direct trade execution through MT5 API
- **Position Management**: Automatic monitoring and closure of positions
- **Account Monitoring**: Real-time balance, equity, and margin tracking

### 📈 **Professional Dashboard**
- **Real-time Monitoring**: Live performance metrics and trading signals
- **Interactive Charts**: Performance visualization with Chart.js
- **System Controls**: Start/stop trading and manual signal injection
- **Connection Status**: MT5 and system connectivity monitoring

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MetaTrader 5  │◄──►│  WebSocket Bridge│◄──►│  Python Server  │
│   Expert Advisor│    │     (FastAPI)    │    │    (ML System)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                              ┌─────────┴─────────┐
                                              │  Data Processing  │
                                              │  ML Models        │
                                              │  Meta-Learning    │
                                              │  Strategy Manager │
                                              └───────────────────┘
```

## Quick Start

### Prerequisites

1. **MetaTrader 5** installed and running
2. **Python 3.8+** environment
3. **Git** for cloning the repository
4. **Internet connection** for API calls and data feeds

### Installation

1. **Clone the repository**
```bash
git remote add origin git@github.com:legendary-daniel/Helios.git
git branch -M Legendary
git push -u origin Legendary
cd helios-ml-trading
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure the system**
```bash
# Copy and edit configuration
cp config/config.json.example config/config.json
# Edit config.json with your MT5 credentials and preferences
```

4. **Set up MT5 Expert Advisor**
```bash
# Copy the EA file to your MT5 Experts folder
cp deployed/HeliosML_EA.mq5 <MT5_Data_Folder>/MQL5/Experts/
```

5. **Compile and attach the EA in MetaTrader 5**

### Running the System

1. **Start the Python server**
```bash
python src/helios_server.py
```

2. **Open the dashboard**
Navigate to `http://localhost:8765` in your browser

3. **Configure the EA in MT5**
- Attach `HeliosML_EA` to your chart
- Set the WebSocket URL to `ws://localhost:8765`
- Configure trading parameters
- Enable automated trading

4. **Start trading**
- Click "Start Trading" in the dashboard
- Monitor signals and performance
- Adjust strategies as needed

## Deployment Options

### Free Cloud Platforms

#### 🚀 **Railway.app (Recommended)**
- **$5 free credit monthly**
- 500 execution hours
- 1GB RAM, 1GB storage
- No cold starts

**Deployment:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

#### 🎨 **Render.com**
- **750 hours/month free**
- 1GB RAM
- Auto-sleep after 15 minutes
- Easy GitHub integration

**Deployment:**
1. Connect GitHub repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python src/helios_server.py`

#### 🐙 **Heroku (Paid)**
- **$7/month minimum**
- Reliable and mature platform
- Good for production use

**Deployment:**
```bash
# Install Heroku CLI, then:
heroku create your-app-name
git push heroku main
```

### Docker Deployment

```bash
# Build and run with Docker
docker build -t helios-ml-trading .
docker run -p 8765:8765 helios-ml-trading

# Or use docker-compose
docker-compose up -d
```

## Configuration

### MT5 Connection
```json
{
  "mt5": {
    "login": 123456,
    "password": "your_password",
    "server": "Your-Broker-Server",
    "timeout": 60000
  }
}
```

### Trading Parameters
```json
{
  "risk": {
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 0.05,
    "max_open_positions": 5,
    "position_sizing_method": "kelly"
  },
  "ml": {
    "confidence_threshold": 0.7,
    "model_type": "ensemble",
    "retrain_interval_hours": 6
  }
}
```

### Strategies Configuration
```json
{
  "strategy": {
    "strategies": [
      {
        "name": "trend_following",
        "enabled": true,
        "parameters": {
          "fast_ema": 12,
          "slow_ema": 26,
          "rsi_period": 14
        }
      }
    ]
  }
}
```

## API Documentation

### WebSocket API

#### Connect to MT5
```javascript
const ws = new WebSocket('ws://localhost:8765/ws/mt5');
```

#### Send Trading Signal
```javascript
ws.send(JSON.stringify({
  type: 'trade_signal',
  data: {
    symbol: 'EURUSD',
    signal_type: 'buy',
    confidence: 0.85,
    price: 1.1234,
    stop_loss: 1.1200,
    take_profit: 1.1300,
    strategy: 'trend_following'
  }
}));
```

#### Request Status
```javascript
ws.send(JSON.stringify({
  type: 'status_request'
}));
```

### REST API Endpoints

- `GET /api/status` - System status
- `GET /api/signals` - Recent signals
- `GET /api/strategies` - Strategy performance
- `POST /api/start-trading` - Start trading
- `POST /api/stop-trading` - Stop trading
- `GET /health` - Health check

## Strategy Details

### 1. Trend Following Strategy
- **Indicators**: EMA(12/26), RSI(14)
- **Signal**: EMA crossover with RSI confirmation
- **Market Conditions**: Trending markets
- **Risk**: 2% per trade, ATR-based stops

### 2. Mean Reversion Strategy
- **Indicators**: Bollinger Bands(20,2), RSI(14)
- **Signal**: Price at bands with RSI extreme
- **Market Conditions**: Sideways/ranging markets
- **Risk**: 1.5% per trade

### 3. Breakout Strategy
- **Indicators**: Price momentum, Volume threshold
- **Signal**: Break above/below recent high/low
- **Market Conditions**: High volatility
- **Risk**: 2.5% per trade

### 4. Scalping Strategy
- **Indicators**: Tick-based momentum
- **Signal**: Quick price movements
- **Market Conditions**: High activity sessions
- **Risk**: 1% per trade

## Performance Monitoring

### Key Metrics
- **Total Trades**: Number of executed trades
- **Success Rate**: Percentage of profitable trades
- **Daily P&L**: Daily profit/loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline

### Real-time Dashboard
- Live performance charts
- Signal visualization
- Connection status
- Account metrics
- Strategy performance

## Risk Warnings

⚠️ **IMPORTANT DISCLAIMERS**

1. **No Financial Advice**: This software is for educational purposes only
2. **Risk of Loss**: Trading involves substantial risk of loss
3. **Past Performance**: Does not guarantee future results
4. **Paper Trading**: Test thoroughly before live trading
5. **Professional Advice**: Consult financial advisors before trading

## Development

### Project Structure
```
helios-ml-trading/
├── src/
│   ├── config.py           # Configuration management
│   ├── data_processor.py   # Market data processing
│   ├── ml_models.py        # Machine learning models
│   ├── meta_learning.py    # Meta-learning engine
│   ├── trading_strategies.py # Trading strategies
│   ├── mt5_interface.py    # MT5 communication
│   ├── helios_system.py    # Main coordinator
│   └── helios_server.py    # FastAPI server
├── deployed/
│   ├── HeliosML_EA.mq5     # MetaTrader 5 EA
│   └── dashboard.html      # Web dashboard
├── deployment/
│   └── deploy_manager.py   # Deployment tools
├── config/
│   └── config.json         # Configuration file
├── logs/                   # Log files
├── models/                 # ML model storage
└── data/                   # Market data cache
```

### Adding New Strategies

1. **Create strategy class** in `src/trading_strategies.py`
2. **Register in StrategyManager** initialization
3. **Add configuration** in `config/config.json`
4. **Test with historical data**
5. **Deploy and monitor performance**

### Custom ML Models

1. **Inherit from BaseModel** in `src/ml_models.py`
2. **Implement required methods** (fit, predict, etc.)
3. **Add to ModelFactory**
4. **Configure in ensemble settings**
5. **Validate with backtesting**

## Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Check if Python server is running
- Verify firewall settings
- Ensure WebSocket URL is correct

**MT5 EA Not Receiving Signals**
- Confirm EA is attached to chart
- Check MT5 terminal is running
- Verify WebSocket connection in EA settings

**Models Not Loading**
- Check `models/` directory permissions
- Verify model files exist
- Review logs for error messages

**Poor Trading Performance**
- Review strategy configuration
- Check market regime detection
- Analyze risk management settings
- Consider model retraining

### Logs and Debugging

```bash
# View system logs
tail -f logs/helios_trading.log

# Check server logs
tail -f logs/helios_server.log

# Enable debug logging
export HELIOS_LOG_LEVEL=DEBUG
python src/helios_server.py
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: Check the `docs/` folder
- **Issues**: Open GitHub issues for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Email**: danielannan212@gmail.com
  

## Changelog

### Version 1.0.0 (2025-01-27)
- Initial release
- Multi-strategy trading system
- Machine learning integration
- MetaTrader 5 Expert Advisor
- Web-based dashboard
- Free cloud deployment support
- Comprehensive risk management
- Real-time performance monitoring

---

**Helios ML Trading System** - Automate. Adapt. Ascend.

*Professional machine learning trading system for the modern trader.*# Helios
# BOT-s
