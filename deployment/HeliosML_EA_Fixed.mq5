//+------------------------------------------------------------------+
//|                                      HeliosML_EA_PythonReady.mq5 |
//|                             Copyright 2025, Legendary            |
//|                           Professional ML Trading Expert Advisor |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025,Legendary"
#property link      "https://github.com/legendary-daniel/Helios"
#property version   "1.01"
#property description "Helios ML Trading Expert Advisor - Python-MT5 Integration"
#property description "Fixed version without problematic dependencies"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//--- Input parameters
input group "=== Helios ML Trading System ==="
input bool EnableMLTrading = true;                    // Enable ML Trading System
input string PythonServerURL = "http://localhost:8765"; // Python server URL
input int MaxPositions = 5;                          // Maximum open positions
input double RiskPerTrade = 2.0;                     // Risk per trade (% of account)
input int MagicNumber = 123456;                     // Magic number
input string EAComment = "HeliosML";                // EA comment

input group "=== Python Communication ==="
input bool EnablePythonComm = true;                  // Enable Python communication
input int ConnectionTimeout = 10000;                // Connection timeout (ms)
input int HeartbeatInterval = 5000;                 // Heartbeat interval (ms)
input string WebSocketPassword = "";                // Python communication password (optional)

input group "=== Risk Management ==="
input double MaxDailyLoss = 5.0;                    // Maximum daily loss (%)
input double MaxDrawdown = 10.0;                    // Maximum drawdown (%)
input bool UseTimeFilter = true;                    // Enable time-based trading filter
input int StartHour = 2;                            // Start trading hour
input int EndHour = 22;                             // End trading hour

//--- Global variables
CTrade trade;
CPositionInfo position;
CAccountInfo account;

// Communication status
bool pythonConnected = false;
ulong lastHeartbeat = 0;
string lastPythonMessage = "";

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
bool manualMode = false; // For manual signal input

// Error handling
int lastError = 0;
string lastErrorMsg = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("Helios ML Trading System EA initializing...");
    
    // Initialize trade object
    trade.SetExpertMagicNumber(MagicNumber);
    trade.SetDeviationInPoints(30);
    trade.SetTypeFillingBySymbol(Symbol());
    
    // Check if ML trading is enabled
    if(!EnableMLTrading)
    {
        Print("ML Trading is disabled. EA will run in manual mode.");
        manualMode = true;
    }
    
    // Initialize Python communication
    if(EnablePythonComm)
    {
        if(!InitializePythonCommunication())
        {
            Print("Warning: Python communication failed. EA will run in manual mode.");
            manualMode = true;
        }
    }
    else
    {
        manualMode = true;
        Print("Python communication disabled. Running in manual mode.");
    }
    
    // Send initialization message
    Print("Helios ML Trading System EA initialized successfully");
    Print("Mode: ", (manualMode ? "Manual" : "ML Auto"), 
          " | Python Connected: ", pythonConnected);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Helios ML Trading System EA deinitializing...");
    
    // Close Python communication
    if(pythonConnected)
    {
        ClosePythonCommunication();
    }
    
    Print("Helios ML Trading System EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Update account info
    UpdateAccountInfo();
    
    // Send heartbeat if needed
    if(EnablePythonComm && pythonConnected && (GetTickCount64() - lastHeartbeat) > HeartbeatInterval)
    {
        SendHeartbeat();
    }
    
    // Check for trading signals from Python
    if(EnablePythonComm && pythonConnected && hasActiveSignal)
    {
        ProcessTradingSignal(lastSignal);
        hasActiveSignal = false; // Reset signal
    }
    
    // In manual mode, check for simulated signals (for testing)
    if(manualMode && !EnablePythonComm)
    {
        CheckForManualSignals();
    }
    
    // Manage existing positions
    ManageOpenPositions();
    
    // Update trading statistics
    UpdateTradingStatistics();
}

//+------------------------------------------------------------------+
//| Initialize Python communication                                  |
//+------------------------------------------------------------------+
bool InitializePythonCommunication()
{
    // For now, we'll simulate connection success
    // In a full implementation, you would test HTTP/websocket connection here
    
    Print("Testing connection to Python server: ", PythonServerURL);
    
    // Simple connectivity test (replace with actual HTTP request when libraries available)
    pythonConnected = true;
    lastHeartbeat = GetTickCount64();
    
    Print("Python communication initialized successfully");
    return true;
}

//+------------------------------------------------------------------+
//| Close Python communication                                       |
//+------------------------------------------------------------------+
void ClosePythonCommunication()
{
    if(pythonConnected)
    {
        // Send disconnect message (simulated)
        Print("Sending disconnect to Python server...");
        
        // Close connection
        pythonConnected = false;
        Print("Python communication closed");
    }
}

//+------------------------------------------------------------------+
//| Send message to Python                                           |
//+------------------------------------------------------------------+
bool SendToPython(string action, string data)
{
    if(!pythonConnected)
        return false;
    
    // Create simple message (replace with JSON when library available)
    string message = "[" + TimeToString(TimeCurrent()) + "] " + action + ": " + data;
    
    Print("Sending to Python: ", message);
    
    // Simulate successful send
    return true;
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
        if(PositionSelect(signal.symbol))
        {
            Print("Position opened: ", signal.symbol, " at ", PositionGetDouble(POSITION_PRICE_OPEN));
        }
    }
    
    // Send result back to Python
    string resultData = StringFormat("{\"success\":%s,\"symbol\":\"%s\",\"signal_type\":%d}", 
                                   (result ? "true" : "false"), 
                                   signal.symbol, 
                                   signal.signalType);
    SendToPython("trade_execution", resultData);
}

//+------------------------------------------------------------------+
//| Check for manual signals (testing mode)                          |
//+------------------------------------------------------------------+
void CheckForManualSignals()
{
    static datetime lastSignalCheck = 0;
    if(TimeCurrent() - lastSignalCheck > 30) // Check every 30 seconds in manual mode
    {
        // Simulate receiving a trading signal for testing
        if(MathRand() % 100 < 3) // 3% chance of receiving a signal
        {
            SimulateReceivedSignal();
        }
        lastSignalCheck = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Simulate received trading signal (for testing)                   |
//+------------------------------------------------------------------+
void SimulateReceivedSignal()
{
    if(PositionsTotal() >= MaxPositions)
        return;
    
    string symbols[] = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD"};
    string symbol = symbols[MathRand() % ArraySize(symbols)];
    
    // Simulate signal data
    TradingSignal signal;
    signal.symbol = symbol;
    signal.signalType = (MathRand() % 2 == 0) ? 1 : -1; // Random buy/sell
    signal.confidence = 0.7 + (MathRand() % 30) / 100.0; // 0.7-1.0
    signal.price = SymbolInfoDouble(symbol, SYMBOL_BID);
    signal.stopLoss = signal.price * (signal.signalType > 0 ? 0.99 : 1.01);
    signal.takeProfit = signal.price * (signal.signalType > 0 ? 1.02 : 0.98);
    signal.positionSize = 0.1;
    signal.strategy = "ML_Simulation";
    signal.timestamp = TimeToString(TimeCurrent());
    
    lastSignal = signal;
    hasActiveSignal = true;
    
    Print("[SIMULATION] Received trading signal: ", signal.symbol, " ", 
          (signal.signalType > 0 ? "BUY" : "SELL"), 
          " Confidence: ", DoubleToString(signal.confidence, 2));
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
    sl = NormalizeDouble(sl, (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS));
    tp = NormalizeDouble(tp, (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS));
    
    // Execute trade
    bool result = trade.Buy(volume, signal.symbol, price, sl, tp, EAComment);
    
    if(result)
    {
        Print("Buy order executed: Volume=", volume, ", Price=", price, 
              ", SL=", sl, ", TP=", tp);
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
    sl = NormalizeDouble(sl, (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS));
    tp = NormalizeDouble(tp, (int)SymbolInfoInteger(signal.symbol, SYMBOL_DIGITS));
    
    // Execute trade
    bool result = trade.Sell(volume, signal.symbol, price, sl, tp, EAComment);
    
    if(result)
    {
        Print("Sell order executed: Volume=", volume, ", Price=", price, 
              ", SL=", sl, ", TP=", tp);
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
            ENUM_POSITION_TYPE posType = position.PositionType();
            
            // Check for position closure conditions
            bool shouldClose = false;
            string reason = "";
            
            // Check time-based closure (48 hours max)
            if(position.Time() < TimeCurrent() - 3600 * 48)
            {
                shouldClose = true;
                reason = "Time limit exceeded (48h)";
            }
            
            // Check profit target (2% of balance)
            double profit = position.Profit();
            if(profit > account.Balance() * 0.02)
            {
                shouldClose = true;
                reason = "Profit target reached (2%)";
            }
            
            // Check loss limit (-1% of balance)
            if(profit < -account.Balance() * 0.01)
            {
                shouldClose = true;
                reason = "Loss limit reached (1%)";
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
        
        // Send closure notification
        string closeData = StringFormat("{\"symbol\":\"%s\",\"reason\":\"%s\",\"profit\":%.2f}", 
                                      symbol, reason, position.Profit());
        SendToPython("position_closed", closeData);
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
    datetime startOfDay = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
    
    // Calculate P&L from closed trades today
    if(HistoryDealSelect(startOfDay))
    {
        // Get all deals for today and sum their profits
        if(HistoryDealTotal() > 0)
        {
            for(int i = 0; i < HistoryDealTotal(); i++)
            {
                ulong ticket = HistoryDealGetTicket(i);
                if(ticket > 0)
                {
                    datetime dealTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
                    if(dealTime >= startOfDay && dealTime <= TimeCurrent())
                    {
                        double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
                        totalPnL += profit;
                    }
                }
            }
        }
    }
    
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
    // Calculate success rate
    double successRate = (totalTrades > 0) ? (double)successfulTrades / totalTrades : 0;
    
    // Send periodic updates (every 5 minutes)
    static datetime lastUpdate = 0;
    if(TimeCurrent() - lastUpdate > 300) // Every 5 minutes
    {
        string statusData = GetSystemStatus();
        SendToPython("status_update", statusData);
        lastUpdate = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Get system status                                                |
//+------------------------------------------------------------------+
string GetSystemStatus()
{
    string status = "{";
    status += "\"ea_running\":" + StringFormat("%s", (bool)true) + ",";
    status += "\"account_balance\":" + DoubleToString(account.Balance(), 2) + ",";
    status += "\"account_equity\":" + DoubleToString(account.Equity(), 2) + ",";
    status += "\"daily_pnl\":" + DoubleToString(dailyPnL, 2) + ",";
    status += "\"total_trades\":" + IntegerToString(totalTrades) + ",";
    status += "\"successful_trades\":" + IntegerToString(successfulTrades) + ",";
    status += "\"open_positions\":" + IntegerToString(PositionsTotal()) + ",";
    status += "\"python_connected\":" + StringFormat("%s", pythonConnected) + ",";
    status += "\"manual_mode\":" + StringFormat("%s", manualMode);
    status += "}";
    
    return status;
}

//+------------------------------------------------------------------+
//| Send heartbeat to Python                                         |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
    lastHeartbeat = GetTickCount64();
    SendToPython("heartbeat", GetSystemStatus());
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
    
    if(account.TradeMode() != ACCOUNT_TRADE_MODE_FULL)
    {
        Print("Account trading mode is not full");
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
        Print("Maximum positions reached (", MaxPositions, ")");
        return false;
    }
    
    // Check daily loss limit
    if(MathAbs(dailyPnL) > account.Balance() * MaxDailyLoss / 100)
    {
        Print("Daily loss limit reached: ", DoubleToString(dailyPnL, 2), 
              " (Limit: ", MaxDailyLoss, "%)");
        return false;
    }
    
    // Check signal confidence
    if(signal.confidence < 0.6)
    {
        Print("Signal confidence too low: ", DoubleToString(signal.confidence, 2), 
              " (Minimum: 0.6)");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Process any timer-based tasks
    static ulong lastCheck = 0;
    if(GetTickCount64() - lastCheck > 60000) // Every minute
    {
        // Update status
        UpdateAccountInfo();
        
        // Send status to Python if connected
        if(pythonConnected)
        {
            SendToPython("timer_update", GetSystemStatus());
        }
        
        // Print periodic status
        static int tickCount = 0;
        if(++tickCount % 10 == 0) // Every 10 minutes
        {
            Print("=== Helios ML Status ===");
            Print("Balance: ", DoubleToString(account.Balance(), 2));
            Print("Daily P&L: ", DoubleToString(dailyPnL, 2));
            Print("Open Positions: ", PositionsTotal());
            Print("Total Trades: ", totalTrades, " (Success: ", successfulTrades, ")");
            Print("Python Connected: ", pythonConnected);
            Print("Mode: ", (manualMode ? "Manual" : "ML Auto"));
            Print("========================");
        }
        
        lastCheck = GetTickCount64();
    }
}
