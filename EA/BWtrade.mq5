#property strict

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

int OnInit()
{
    ArrayResize(LastClosePrice, ArraySize(CurrencyPairs));
    ArrayResize(PredictValue, ArraySize(CurrencyPairs));
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
        PredictValue[i] = GetPrediction(symbol);

        // Ensure only one trade per currency pair
        bool openOrderExists = false;
        for (int j = PositionsTotal() - 1; j >= 0; j--)
        {
            if (PositionSelect(j))
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
            PlaceOrder(symbol, ORDER_TYPE_BUY);
        }
        // Sell condition
        else if (PredictValue[i] < LastClosePrice[i])
        {
            PlaceOrder(symbol, ORDER_TYPE_SELL);
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
    char result[4096];
    string headers;
    int timeout = 5000;
    int result_size = sizeof(result);
    int res = WebRequest("POST", url, "", timeout, jsonData, StringLen(jsonData), result, result_size, headers);
    if (res == -1)
    {
        Print("Error in WebRequest. Error code: ", GetLastError());
        return 0.0;
    }

    string resultStr = CharArrayToString(result, result_size);
    int pos = StringFind(resultStr, ":");
    if (pos != -1)
    {
        string value = StringSubstr(resultStr, pos + 1);
        double prediction = StringToDouble(value);
        return prediction;
    }
    return 0.0;
}

void PlaceOrder(string symbol, int orderType)
{
    double lotSize = 0.1;  // Adjust position size as needed
    double price = (orderType == ORDER_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
    double sl = (orderType == ORDER_TYPE_BUY) ? price - 50 * SymbolInfoDouble(symbol, SYMBOL_POINT) : price + 50 * SymbolInfoDouble(symbol, SYMBOL_POINT);
    double tp = (orderType == ORDER_TYPE_BUY) ? price + 100 * SymbolInfoDouble(symbol, SYMBOL_POINT) : price - 100 * SymbolInfoDouble(symbol, SYMBOL_POINT);

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
        Print("Error opening order for ", symbol, ". Error code: ", GetLastError());
    }
    else
    {
        Print("Order opened successfully for ", symbol, ". Ticket: ", result.order);
    }
}
