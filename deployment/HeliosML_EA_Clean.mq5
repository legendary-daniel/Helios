//+------------------------------------------------------------------+
//|                                      HeliosML_EA_PythonReady.mq5 |
//|                             Copyright 2025, Legendary            |
//|                           Professional ML Trading Expert Advisor |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025,Legendary"
#property link      "https://github.com/legendary-daniel/Helios"
#property version   "1.02"
#property description "Clean version - Minimal dependencies, maximum compatibility"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//--- Input parameters
input group "=== Helios ML Trading System ==="
input bool EnableMLTrading = true;                    // Enable ML Trading System
input int MaxPositions = 3;                          // Maximum open positions
input double RiskPerTrade = 1.0;                     // Risk per trade (% of account)
input int MagicNumber = 123456;                     // Magic number
input string EAComment = "HeliosML";                // EA comment

input group "=== Risk Management ==="
input double MaxDailyLoss = 3.0;                    // Maximum daily loss (%)
input bool UseTimeFilter = true;                    // Enable time-based trading filter
input int StartHour = 2;                            // Start trading hour
input int EndHour = 22;                             // End trading hour

//--- Global variables
CTrade trade;
CPositionInfo position;
CAccountInfo account;

// Trading statistics
int totalTrades = 0;
int successfulTrades = 0;
double dailyPnL = 0.0;
datetime lastTradeTime = 0;

// Signal management
struct TradingSignal
{
   string symbol;
   int signalType;  // 1=buy, -1=sell, 0=close
   double confidence;
   double price;
   double stopLoss;
   double takeProfit;
   double positionSize;
   string strategy;
   string timestamp;
};

TradingSignal lastSignal;
bool hasActiveSignal = false;
bool manualMode = true; // Always manual mode for compatibility

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("Helios ML Trading System EA initializing (Clean Version)...");
    
    // Initialize trade object
    trade.SetExpertMagicNumber(MagicNumber);
    trade.SetDeviationInPoints(30);
    trade.SetTypeFillingBySymbol(Symbol());
    
    // Always manual mode for compatibility
    manualMode = true;
    
    // Send initialization message
    Print("Helios ML Trading System EA initialized successfully");
    Print("Mode: Manual | Max Positions: ", MaxPositions);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Helios ML Trading System EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Update account info
    UpdateAccountInfo();
    
    // Check for trading signals
    if(hasActiveSignal)
    {
        ProcessTradingSignal(lastSignal);
        hasActiveSignal = false; // Reset signal
    }
    
    // Simulate signals for testing (every 60 seconds)
    static datetime lastSignalCheck = 0;
    if(TimeCurrent() - lastSignalCheck > 60)
    {
        SimulateReceivedSignal();
        lastSignalCheck = TimeCurrent();
    }
    
    // Manage existing positions
    ManageOpenPositions();
    
    // Update trading statistics
    UpdateTradingStatistics();
}

//+------------------------------------------------------------------+
//| Simulate received trading signal (for testing)                   |
//+------------------------------------------------------------------+
void SimulateReceivedSignal()
{
    if(PositionsTotal() >= MaxPositions)
        return;
    
    if(MathRand() % 100 < 2) // 2% chance
    {
        string symbols[] = {"EURUSD", "GBPUSD", "USDJPY"};
        string symbol = symbols[MathRand() % 3];
        
        TradingSignal signal;
        signal.symbol = symbol;
        signal.signalType = (MathRand() % 2 == 0) ? 1 : -1;
        signal.confidence = 0.7;
        signal.price = SymbolInfoDouble(symbol, SYMBOL_BID);
        signal.stopLoss = signal.price * (signal.signalType > 0 ? 0.99 : 1.01);
        signal.takeProfit = signal.price * (signal.signalType > 0 ? 1.02 : 0.98);
        signal.positionSize = 0.01;
        signal.strategy = "Test_Signal";
        signal.timestamp = TimeToString(TimeCurrent());
        
        lastSignal = signal;
        hasActiveSignal = true;
        
        Print("[SIMULATION] Signal: ", symbol, " ", 
              (signal.signalType > 0 ? "BUY" : "SELL"), 
              " Confidence: 0.70");
    }
}

//+------------------------------------------------------------------+
//| Process trading signal                                           |
//+------------------------------------------------------------------+
void ProcessTradingSignal(TradingSignal& signal)
{
    // Check if trading is allowed
    if(!IsTradeAllowed())
        return;
    
    // Check time filter
    if(UseTimeFilter && !IsWithinTradingHours())
        return;
    
    // Check risk management
    if(!CheckRiskManagement(signal))
        return;
    
    // Execute the trade
    bool result = false;
    
    if(signal.signalType == 1) // Buy
    {
        result = OpenBuyPosition(signal);
    }
    else if(signal.signalType == -1) // Sell
    {
        result = OpenSellPosition(signal);
    }
    
    // Update statistics
    if(result)
    {
        totalTrades++;
        Print("Trade executed: ", signal.symbol, " Volume: ", signal.positionSize);
    }
}

//+------------------------------------------------------------------+
//| Open buy position                                                |
//+------------------------------------------------------------------+
bool OpenBuyPosition(TradingSignal& signal)
{
    double volume = CalculatePositionSize(signal);
    double price = SymbolInfoDouble(signal.symbol, SYMBOL_ASK);
    double sl = signal.stopLoss;
    double tp = signal.takeProfit;
    
    // Validate parameters
    if(volume <= 0 || sl <= 0 || tp <= 0)
        return false;
    
    // Normalize prices
    int digits = (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS);
    sl = NormalizeDouble(sl, digits);
    tp = NormalizeDouble(tp, digits);
    
    // Execute trade
    bool result = trade.Buy(volume, signal.symbol, price, sl, tp, EAComment);
    
    if(result)
    {
        Print("Buy order executed: Volume=", volume, ", Price=", price);
    }
    else
    {
        Print("Buy order failed. Error: ", GetLastError());
    }
    
    return result;
}

//+------------------------------------------------------------------+
//| Open sell position                                               |
//+------------------------------------------------------------------+
bool OpenSellPosition(TradingSignal& signal)
{
    double volume = CalculatePositionSize(signal);
    double price = SymbolInfoDouble(signal.symbol, SYMBOL_BID);
    double sl = signal.stopLoss;
    double tp = signal.takeProfit;
    
    // Validate parameters
    if(volume <= 0 || sl <= 0 || tp <= 0)
        return false;
    
    // Normalize prices
    int digits = (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS);
    sl = NormalizeDouble(sl, digits);
    tp = NormalizeDouble(tp, digits);
    
    // Execute trade
    bool result = trade.Sell(volume, signal.symbol, price, sl, tp, EAComment);
    
    if(result)
    {
        Print("Sell order executed: Volume=", volume, ", Price=", price);
    }
    else
    {
        Print("Sell order failed. Error: ", GetLastError());
    }
    
    return result;
}

//+------------------------------------------------------------------+
//| Calculate position size based on risk management                 |
//+------------------------------------------------------------------+
double CalculatePositionSize(TradingSignal& signal)
{
    double balance = account.Balance();
    double riskAmount = balance * RiskPerTrade / 100.0;
    
    double price = (signal.signalType > 0) ? 
                   SymbolInfoDouble(signal.symbol, SYMBOL_ASK) : 
                   SymbolInfoDouble(signal.symbol, SYMBOL_BID);
    
    double stopDistance = MathAbs(price - signal.stopLoss);
    
    if(stopDistance <= 0)
        return 0;
    
    double lotSize = riskAmount / stopDistance;
    
    // Normalize to symbol specifications
    double minLot = SymbolInfoDouble(signal.symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(signal.symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(signal.symbol, SYMBOL_VOLUME_STEP);
    
    lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
    lotSize = MathRound(lotSize / lotStep) * lotStep;
    
    return lotSize;
}

//+------------------------------------------------------------------+
//| Manage open positions                                            |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(position.SelectByIndex(i))
        {
            string symbol = position.Symbol();
            
            // Check for position closure conditions
            bool shouldClose = false;
            string reason = "";
            
            // Check time-based closure (24 hours max)
            if(position.Time() < TimeCurrent() - 86400) // 24 hours
            {
                shouldClose = true;
                reason = "Time limit (24h)";
            }
            
            // Check profit target (1% of balance)
            double profit = position.Profit();
            if(profit > account.Balance() * 0.01)
            {
                shouldClose = true;
                reason = "Profit target (1%)";
            }
            
            // Close position if needed
            if(shouldClose)
            {
                ClosePosition(symbol, reason);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Close position                                                   |
//+------------------------------------------------------------------+
bool ClosePosition(string symbol, string reason)
{
    if(!position.Select(symbol))
        return false;
    
    bool result = false;
    
    if(position.PositionType() == POSITION_TYPE_BUY)
    {
        result = trade.Sell(position.Volume(), symbol, 0, 0, 0, 
                           EAComment + "_Close_" + reason);
    }
    else
    {
        result = trade.Buy(position.Volume(), symbol, 0, 0, 0, 
                          EAComment + "_Close_" + reason);
    }
    
    if(result)
    {
        Print("Position closed: ", symbol, " Reason: ", reason);
        
        // Update statistics
        if(position.Profit() > 0)
            successfulTrades++;
    }
    
    return result;
}

//+------------------------------------------------------------------+
//| Update account information                                       |
//+------------------------------------------------------------------+
void UpdateAccountInfo()
{
    // Refresh account info
    account.Refresh();
    
    // Update daily PnL
    dailyPnL = CalculateDailyPnL();
}

//+------------------------------------------------------------------+
//| Calculate daily P&L                                              |
//+------------------------------------------------------------------+
double CalculateDailyPnL()
{
    double totalPnL = 0;
    
    // Add unrealized P&L from open positions
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(position.SelectByIndex(i))
        {
            totalPnL += position.Profit();
        }
    }
    
    return totalPnL;
}

//+------------------------------------------------------------------+
//| Update trading statistics                                        |
//+------------------------------------------------------------------+
void UpdateTradingStatistics()
{
    // Send periodic updates (every 5 minutes)
    static datetime lastUpdate = 0;
    if(TimeCurrent() - lastUpdate > 300)
    {
        Print("=== Status ===");
        Print("Balance: ", account.Balance());
        Print("Daily P&L: ", dailyPnL);
        Print("Open Positions: ", PositionsTotal());
        Print("Total Trades: ", totalTrades);
        Print("Success Rate: ", (totalTrades > 0) ? (double)successfulTrades / totalTrades : 0);
        Print("================");
        lastUpdate = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Check if trading is allowed                                      |
//+------------------------------------------------------------------+
bool IsTradeAllowed()
{
    if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
    {
        Print("Trading is not allowed in terminal");
        return false;
    }
    
    if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
    {
        Print("EA trading is not allowed");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Check if within trading hours                                    |
//+------------------------------------------------------------------+
bool IsWithinTradingHours()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    
    int currentHour = dt.hour;
    
    return (currentHour >= StartHour && currentHour <= EndHour);
}

//+------------------------------------------------------------------+
//| Check risk management                                            |
//+------------------------------------------------------------------+
bool CheckRiskManagement(TradingSignal& signal)
{
    // Check maximum open positions
    if(PositionsTotal() >= MaxPositions)
    {
        Print("Maximum positions reached");
        return false;
    }
    
    // Check daily loss limit
    if(dailyPnL < -account.Balance() * MaxDailyLoss / 100)
    {
        Print("Daily loss limit reached");
        return false;
    }
    
    // Check signal confidence
    if(signal.confidence < 0.6)
    {
        Print("Signal confidence too low");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
    static ulong lastCheck = 0;
    if(GetTickCount64() - lastCheck > 60000) // Every minute
    {
        UpdateAccountInfo();
        
        lastCheck = GetTickCount64();
    }
}
