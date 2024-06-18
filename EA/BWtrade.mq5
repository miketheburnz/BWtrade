#include <stdlib.mqh>

input string WebServiceURL = "http://127.0.0.1:5000/predict";
input int TimerInterval = 60;  // Interval for timer events in seconds
string CurrencyPairs[] = {
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
    "AUDJPY", "CHFJPY", "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD", "GBPNZD", "AUDCAD", "AUDCHF",
    "AUDNZD", "CADCHF", "CADJPY", "NZDJPY", "NZDCHF", "USDRUB", "USDZAR", "USDSGD", "USDHKD", "USDTRY",
    "USDSEK", "USDDKK", "USDNOK", "USDPLN", "USDMXN", "USDCNH", "USDHUF", "USDTHB", "USDILS", "USDCLP",
    "USDCOP", "USDBRL", "USDKRW", "USDINR", "USDIDR", "USDPHP", "USDMYR", "USDVND"
};

double LastClosePrice[];
double PredictValue[];
double ATR[];

int OnInit()
{
    ArrayResize(LastClosePrice, ArraySize(CurrencyPairs));
    ArrayResize(PredictValue, ArraySize(CurrencyPairs));
    ArrayResize(ATR, ArraySize(CurrencyPairs));
    EventSetTimer(TimerInterval);
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
    EventKillTimer();
}

void OnTick()
{
    // No action needed here since we are using OnTimer for trading logic
}

void OnTimer()
{
    for (int i = 0; i < ArraySize(CurrencyPairs); i++)
    {
        string symbol = CurrencyPairs[i];
        LastClosePrice[i] = iClose(symbol, PERIOD_H1, 1);
        ATR[i] = iATR(symbol, PERIOD_H1, 14);
        PredictValue[i] = GetPrediction(symbol);

        double profitFactor = GetOptimizationData(symbol, "ProfitFactor");
        if (profitFactor < 1.0) continue; // Skip low performing pairs

        // Ensure only one trade per currency pair
        bool openOrderExists = false;
        for (int j = PositionsTotal() - 1; j >= 0; j--)
        {
            ulong ticket = PositionGetTicket(j);
            if (PositionSelect(ticket))
            {
                string openSymbol = PositionGetString(POSITION_SYMBOL);
                if (openSymbol == symbol)
                {
                    openOrderExists = true;
                    break;  // Skip if there is already an open order for this symbol
                }
            }
        }
        if (openOrderExists) continue;

        // Buy condition
        if (PredictValue[i] > LastClosePrice[i])
        {
            PlaceOrder(symbol, ORDER_TYPE_BUY, ATR[i]);
        }
        // Sell condition
        else if (PredictValue[i] < LastClosePrice[i])
        {
            PlaceOrder(symbol, ORDER_TYPE_SELL, ATR[i]);
        }
    }
}

double GetPrediction(string symbol)
{
    string url = WebServiceURL;
    string jsonData = "{\"data\":[";
    double data[10];

    for (int i = 0; i < 10; i++)
    {
        data[i] = iClose(symbol, PERIOD_H1, i);
        jsonData += DoubleToString(data[i], 6);
        if (i < 9) jsonData += ",";
    }
    jsonData += "], \"pair\":\"" + symbol + "\"}";

    ResetLastError();
    char post_data[];
    char result[];
    string headers;
    int timeout = 5000;

    int data_size = StringToCharArray(jsonData, post_data);

    int res = WebRequest("POST", url, "", "", timeout, post_data, data_size, result, headers);
    if (res == -1)
    {
        int error_code = GetLastError();
        Print("Error in WebRequest. Error code: ", error_code);
        return 0.0;
    }

    string resultStr = CharArrayToString(result);
    int pos = StringFind(resultStr, ":");
    if (pos != -1)
    {
        string value = StringSubstr(resultStr, pos + 1);
        double prediction = StringToDouble(value);
        return prediction;
    }
    return 0.0;
}

void PlaceOrder(string symbol, ENUM_ORDER_TYPE orderType, double atr)
{
    double lotSize = 0.1;  // Adjust position size as needed
    double price = (orderType == ORDER_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
    double sl = (orderType == ORDER_TYPE_BUY) ? price - 1.5 * atr : price + 1.5 * atr;
    double tp = (orderType == ORDER_TYPE_BUY) ? price + 3 * atr : price - 3 * atr;

    MqlTradeRequest request;
    MqlTradeResult result;

    ZeroMemory(request);
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = lotSize;
    request.type = orderType;
    request.price = price;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 3;
    request.magic = 234000;
    request.comment = "Order";

    if (!OrderSend(request, result))
    {
        int error_code = GetLastError();
        Print("Error in OrderSend: ", error_code);
    }
    else
    {
        Print("Order opened successfully for ", symbol, ". Ticket: ", result.order);
    }
}

double GetOptimizationData(string symbol, string metric)
{
    string jsonData = "{\"USDPLN\": {\"ProfitFactor\": 1.508029, \"ExpectedPayoff\": 10.375682, \"Trades\": 176}, \"USDTRY\": {\"ProfitFactor\": 1.465415, \"ExpectedPayoff\": 10.301138, \"Trades\": 167}, \"USDHKD\": {\"ProfitFactor\": 1.405242, \"ExpectedPayoff\": 10.566981, \"Trades\": 159}, \"NZDUSD\": {\"ProfitFactor\": 1.412721, \"ExpectedPayoff\": 9.388817, \"Trades\": 169}, \"USDCNH\": {\"ProfitFactor\": 1.398028, \"ExpectedPayoff\": 8.926287, \"Trades\": 167}, \"EURGBP\": {\"ProfitFactor\": 1.388743, \"ExpectedPayoff\": 8.850659, \"Trades\": 167}, \"EURUSD\": {\"ProfitFactor\": 1.364204, \"ExpectedPayoff\": 8.527219, \"Trades\": 169}, \"USDCAD\": {\"ProfitFactor\": 1.355596, \"ExpectedPayoff\": 8.288706, \"Trades\": 170}, \"USDSEK\": {\"ProfitFactor\": 1.356821, \"ExpectedPayoff\": 8.435602, \"Trades\": 166}, \"USDJPY\": {\"ProfitFactor\": 1.344147, \"ExpectedPayoff\": 8.015394, \"Trades\": 165}, \"GBPUSD\": {\"ProfitFactor\": 1.314455, \"ExpectedPayoff\": 8.087673, \"Trades\": 159}, \"USDCHF\": {\"ProfitFactor\": 1.313254, \"ExpectedPayoff\": 8.070252, \"Trades\": 159}, \"USDZAR\": {\"ProfitFactor\": 1.318121, \"ExpectedPayoff\": 7.597546, \"Trades\": 163}, \"AUDUSD\": {\"ProfitFactor\": 1.291870, \"ExpectedPayoff\": 7.624025, \"Trades\": 159}, \"USDSGD\": {\"ProfitFactor\": 1.288635, \"ExpectedPayoff\": 7.712051, \"Trades\": 156}, \"USDDKK\": {\"ProfitFactor\": 1.265785, \"ExpectedPayoff\": 7.111592, \"Trades\": 157}, \"USDRUB\": {\"ProfitFactor\": 0.0, \"ExpectedPayoff\": 0.0, \"Trades\": 0}}";
    char json[];
    StringToCharArray(jsonData, json);
    string metricValue = JSONGetString(json, symbol + "." + metric);
    return StringToDouble(metricValue);
}

string JSONGetString(char &json[], string path)
{
    string res = "";
    string parts[];
    StringSplit(path, '.', parts);
    string searchStr = "\"" + parts[0] + "\":";
    int start = StringFind(CharArrayToString(json), searchStr) + StringLen(searchStr);
    for (int i = 1; i < ArraySize(parts); i++)
    {
        searchStr = "\"" + parts[i] + "\":";
        start = StringFind(CharArrayToString(json), searchStr, start) + StringLen(searchStr);
    }
    int end = StringFind(CharArrayToString(json), ",", start);
    if (end == -1)
        end = StringFind(CharArrayToString(json), "}", start);
    res = StringSubstr(CharArrayToString(json), start, end - start);
    res = StringTrimLeft(res);
    res = StringTrimRight(res);
    res = StringTrim(res, "\"");
    return res;
}

string StringTrim(string str, string trimChar)
{
    return StringTrimLeft(StringTrimRight(str, trimChar), trimChar);
}

string StringTrimLeft(string str, string trimChar)
{
    int pos = StringFind(str, trimChar);
    while (pos == 0)
    {
        str = StringSubstr(str, 1);
        pos = StringFind(str, trimChar);
    }
    return str;
}

string StringTrimRight(string str, string trimChar)
{
    int pos = StringFind(str, trimChar);
    while (pos == StringLen(str) - 1)
    {
        str = StringSubstr(str, 0, StringLen(str) - 1);
        pos = StringFind(str, trimChar);
    }
    return str;
}
