//@version=5
indicator("Pro Trader System", shorttitle="PRO Trader v4.0", overlay=true)

// ==================== SETTINGS ====================
// Moving Averages
ema20Len = input.int(20, "EMA 20", group="📈 Moving Averages")
ema50Len = input.int(50, "EMA 50", group="📈 Moving Averages")
ema200Len = input.int(200, "EMA 200 (Trend Filter)", group="📈 Moving Averages")

// RSI
rsiLen = input.int(14, "RSI Length", group="📊 RSI")
rsiOB = input.int(70, "Overbought", minval=60, maxval=85, group="📊 RSI")
rsiOS = input.int(30, "Oversold", minval=15, maxval=40, group="📊 RSI")

// MACD
fast = input.int(12, "MACD Fast", group="🔄 MACD")
slow = input.int(26, "MACD Slow", group="🔄 MACD")
sig = input.int(9, "Signal", group="🔄 MACD")

// Trading Rules
useTrendFilter = input.bool(false, "Only Trade WITH EMA200 Trend", group="🎯 Trading Rules")
minBarsGap = input.int(3, "Min Bars Between Signals", minval=1, maxval=20, group="🎯 Trading Rules")
requireConfirm = input.bool(true, "Wait for Confirmation Candle", group="🎯 Trading Rules")

// Risk Management
atrLen = input.int(14, "ATR Length", group="⚠️ Risk Management")
slMult = input.float(2.0, "Stop Loss Multiplier", step=0.5, group="⚠️ Risk Management")
tp1Mult = input.float(3.0, "Take Profit 1", step=0.5, group="⚠️ Risk Management")
tp2Mult = input.float(5.0, "Take Profit 2", step=0.5, group="⚠️ Risk Management")

// Display
showMA = input.bool(true, "Show Moving Averages", group="🎨 Display")
showZones = input.bool(true, "Show Overbought/Oversold Zones", group="🎨 Display")
showLevels = input.bool(true, "Show TP/SL Levels", group="🎨 Display")
showLabels = input.bool(true, "Show Entry/Exit Labels", group="🎨 Display")

// ==================== CALCULATIONS ====================
e20 = ta.ema(close, ema20Len)
e50 = ta.ema(close, ema50Len)
e200 = ta.ema(close, ema200Len)

rsi = ta.rsi(close, rsiLen)

[macdLine, signalLine, hist] = ta.macd(close, fast, slow, sig)
atr = ta.atr(atrLen)

// ==================== TREND ====================
aboveEMA200 = close > e200
belowEMA200 = close < e200
strongBullish = e20 > e50 and e50 > e200
strongBearish = e20 < e50 and e50 < e200

// Trend Status
trendStatus = strongBullish ? "STRONG UP" : strongBearish ? "STRONG DOWN" : aboveEMA200 ? "UP" : "DOWN"
trendColor = strongBullish ? color.green : strongBearish ? color.red : aboveEMA200 ? color.yellow : color.orange

// ==================== MOMENTUM ====================
rsiOversold = rsi < rsiOS
rsiOverbought = rsi > rsiOB
rsiRecovering = rsi[1] < rsiOS and rsi > rsi[1]
rsiWeakening = rsi[1] > rsiOB and rsi < rsi[1]

rsiStatus = rsiOverbought ? "Overbought" : rsiOversold ? "Oversold" : "Neutral"
rsiColor = rsiOverbought ? color.red : rsiOversold ? color.lime : color.yellow

macdBullCross = ta.crossover(macdLine, signalLine)
macdBearCross = ta.crossunder(macdLine, signalLine)
macdRising = hist > hist[1]
macdFalling = hist < hist[1]

macdStatus = macdLine > signalLine ? (macdRising ? "Bullish↑" : "Bullish") : (macdFalling ? "Bearish↓" : "Bearish")
macdColor = macdLine > signalLine and macdRising ? color.lime : macdLine > signalLine ? color.green : macdLine < signalLine and macdFalling ? color.red : color.orange

// ==================== PRICE ACTION ====================
bullCandle = close > open
bearCandle = close < open
bodySize = math.abs(close - open)
avgBody = ta.sma(bodySize, 20)

bullishReversal = bullCandle and bodySize > avgBody * 1.3 and close > high[1]
bearishReversal = bearCandle and bodySize > avgBody * 1.3 and close < low[1]

strongBull = bullCandle and bodySize > avgBody
strongBear = bearCandle and bodySize > avgBody

higherLow = low > low[1] and low > low[2]
lowerHigh = high < high[1] and high < high[2]

candleStatus = bullishReversal ? "Strong↑" : bearishReversal ? "Strong↓" : strongBull ? "Bullish" : strongBear ? "Bearish" : "Weak"

// ==================== VOLUME ====================
hasVolume = volume > 0
volMA = ta.sma(volume, 20)
volConfirmBuy = not hasVolume or volume > volMA * 1.2
volConfirmSell = not hasVolume or volume > volMA * 0.8

// ==================== POSITION MANAGEMENT ====================
var float entry = na
var float sl = na
var float tp1 = na
var float tp2 = na
var float trailStop = na
var bool inTrade = false
var string tradeType = ""
var int entryBar = 0

// ==================== SIGNAL LOGIC ====================
buySetup = (rsiOversold or rsi < rsiOS + 5) and (not useTrendFilter or aboveEMA200)
sellSetup = (rsiOverbought or rsi > rsiOB - 10) and (not useTrendFilter or belowEMA200)

setupStatus = buySetup ? "BUY ZONE" : sellSetup ? "SELL ZONE" : "Neutral"
setupColor = buySetup ? color.lime : sellSetup ? color.red : color.gray

buyTrigger = buySetup[1] and (bullishReversal or strongBull) and (macdBullCross or macdRising) and volConfirmBuy
sellTrigger = sellSetup[1] and (bearishReversal or strongBear or macdBearCross) and volConfirmSell

buyConfirmed = not requireConfirm or (buyTrigger and higherLow)
sellConfirmed = not requireConfirm or (sellTrigger and lowerHigh)

var int lastBuyBar = -999
var int lastSellBar = -999
gapOK = (bar_index - lastBuyBar >= minBarsGap) and (bar_index - lastSellBar >= minBarsGap)

// Only allow signals when NOT in a trade
buySignal = buyConfirmed and gapOK and barstate.isconfirmed and not inTrade
sellSignal = sellConfirmed and gapOK and barstate.isconfirmed and not inTrade

if buySignal
    lastBuyBar := bar_index
if sellSignal
    lastSellBar := bar_index

// Last Signal Info
lastSignalType = lastBuyBar > lastSellBar ? "BUY" : lastSellBar > lastBuyBar ? "SELL" : "-"
lastSignalBars = lastBuyBar > lastSellBar ? bar_index - lastBuyBar : lastSellBar > lastBuyBar ? bar_index - lastSellBar : 0
lastSignalColor = lastSignalType == "BUY" ? color.lime : lastSignalType == "SELL" ? color.red : color.gray

// ==================== ENTRY ====================
if buySignal and not inTrade
    entry := close
    sl := close - atr * slMult
    tp1 := close + atr * tp1Mult
    tp2 := close + atr * tp2Mult
    trailStop := na
    inTrade := true
    tradeType := "LONG"
    entryBar := bar_index
    
if sellSignal and not inTrade
    entry := close
    sl := close + atr * slMult
    tp1 := close - atr * tp1Mult
    tp2 := close - atr * tp2Mult
    trailStop := na
    inTrade := true
    tradeType := "SHORT"
    entryBar := bar_index

// ==================== EXIT LOGIC ====================
bool exitLong = false
bool exitShort = false
var float exitPnL = 0.0

// Alert conditions
var bool alertTP1Long = false
var bool alertTP2Long = false
var bool alertSLLong = false
var bool alertTP1Short = false
var bool alertTP2Short = false
var bool alertSLShort = false
var bool alertTrailLong = false
var bool alertTrailShort = false

// Exit conditions for LONG
if inTrade and tradeType == "LONG"
    // Stop loss hit
    bool slHit = low <= sl
    if slHit
        alertSLLong := true
    
    // Take profit hits
    bool tp1Hit = high >= tp1 and not (high[1] >= tp1)
    bool tp2Hit = high >= tp2
    if tp1Hit
        alertTP1Long := true
    if tp2Hit
        alertTP2Long := true
    
    // Exit on opposite signal, stop loss, or take profit 2
    exitLong := sellSignal or slHit or tp2Hit
    
    // Trailing Stop for LONG
    if close > entry * 1.05
        newTrail = close - atr * slMult * 0.8
        trailStop := na(trailStop) ? newTrail : math.max(trailStop, newTrail)
        if low <= trailStop
            alertTrailLong := true
            exitLong := true

// Exit conditions for SHORT
if inTrade and tradeType == "SHORT"
    // Stop loss hit
    bool slHit = high >= sl
    if slHit
        alertSLShort := true
    
    // Take profit hits
    bool tp1Hit = low <= tp1 and not (low[1] <= tp1)
    bool tp2Hit = low <= tp2
    if tp1Hit
        alertTP1Short := true
    if tp2Hit
        alertTP2Short := true
    
    // Exit on opposite signal, stop loss, or take profit 2
    exitShort := buySignal or slHit or tp2Hit
    
    // Trailing Stop for SHORT
    if close < entry * 0.95
        newTrail = close + atr * slMult * 0.8
        trailStop := na(trailStop) ? newTrail : math.min(trailStop, newTrail)
        if high >= trailStop
            alertTrailShort := true
            exitShort := true

// Calculate P/L BEFORE resetting variables
if exitLong
    exitPnL := (close - entry) / entry * 100
    inTrade := false
    tradeType := ""
    
if exitShort
    exitPnL := (entry - close) / entry * 100
    inTrade := false
    tradeType := ""

// Reset position variables after exit
if exitLong or exitShort
    entry := na
    sl := na
    tp1 := na
    tp2 := na
    trailStop := na
    entryBar := 0

// Position Stats
positionPnL = inTrade ? (tradeType == "LONG" ? (close - entry) / entry * 100 : (entry - close) / entry * 100) : 0.0
riskRewardRatio = inTrade ? math.abs((tp1 - entry) / (entry - sl)) : 0.0
positionStatus = inTrade ? "Running" : "None"
positionColor = positionPnL > 0 ? color.lime : positionPnL < 0 ? color.red : color.gray

// ==================== PLOTS ====================
plot(showMA ? e20 : na, "EMA 20", color=color.yellow, linewidth=2)
plot(showMA ? e50 : na, "EMA 50", color=color.orange, linewidth=2)
plot(showMA ? e200 : na, "EMA 200", color=color.red, linewidth=3)

plotshape(buySignal, "BUY", shape.triangleup, location.belowbar, color=color.lime, size=size.large)
plotshape(sellSignal, "SELL", shape.triangledown, location.abovebar, color=color.red, size=size.large)

// ==================== TP/SL LEVELS ====================
var line entryLine = na
var line slLine = na
var line tp1Line = na
var line tp2Line = na
var line trailLine = na

var label entryLabel = na
var label slLabel = na
var label tp1Label = na
var label tp2Label = na

if showLevels
    // Clear old lines
    if not na(entryLine)
        line.delete(entryLine)
    if not na(slLine)
        line.delete(slLine)
    if not na(tp1Line)
        line.delete(tp1Line)
    if not na(tp2Line)
        line.delete(tp2Line)
    if not na(trailLine)
        line.delete(trailLine)
        
    // Clear old labels
    if not na(entryLabel)
        label.delete(entryLabel)
    if not na(slLabel)
        label.delete(slLabel)
    if not na(tp1Label)
        label.delete(tp1Label)
    if not na(tp2Label)
        label.delete(tp2Label)
    
    // Draw new lines if in trade
    if inTrade
        entryLine := line.new(entryBar, entry, bar_index + 10, entry, color=color.blue, width=2, style=line.style_solid)
        slLine := line.new(entryBar, sl, bar_index + 10, sl, color=color.red, width=2, style=line.style_solid)
        tp1Line := line.new(entryBar, tp1, bar_index + 10, tp1, color=color.green, width=1, style=line.style_dashed)
        tp2Line := line.new(entryBar, tp2, bar_index + 10, tp2, color=color.lime, width=2, style=line.style_dashed)
        
        if not na(trailStop)
            trailLine := line.new(entryBar, trailStop, bar_index + 10, trailStop, color=color.orange, width=2, style=line.style_dotted)
        
        // Labels
        entryLabel := label.new(bar_index + 5, entry, "ENTRY: " + str.tostring(entry, format.mintick), 
             color=color.new(color.blue, 80), textcolor=color.white, style=label.style_label_left, size=size.small)
        slLabel := label.new(bar_index + 5, sl, "SL: " + str.tostring(sl, format.mintick), 
             color=color.new(color.red, 80), textcolor=color.white, style=label.style_label_left, size=size.small)
        tp1Label := label.new(bar_index + 5, tp1, "TP1: " + str.tostring(tp1, format.mintick), 
             color=color.new(color.green, 80), textcolor=color.white, style=label.style_label_left, size=size.small)
        tp2Label := label.new(bar_index + 5, tp2, "TP2: " + str.tostring(tp2, format.mintick), 
             color=color.new(color.lime, 80), textcolor=color.white, style=label.style_label_left, size=size.small)

// Entry/Exit Labels
if showLabels and buySignal
    label.new(bar_index, low, "🟢 BUY\n" + str.tostring(close, format.mintick), 
         color=color.new(color.lime, 20), textcolor=color.white, style=label.style_label_up, size=size.normal)

if showLabels and sellSignal
    label.new(bar_index, high, "🔴 SELL\n" + str.tostring(close, format.mintick), 
         color=color.new(color.red, 20), textcolor=color.white, style=label.style_label_down, size=size.normal)

if showLabels and (exitLong or exitShort)
    exitText = "EXIT\n" + str.tostring(close, format.mintick) + "\nP/L: " + str.tostring(exitPnL, "#.##") + "%"
    wasLong = exitLong
    label.new(bar_index, wasLong ? high : low, exitText, 
         color=color.new(exitPnL > 0 ? color.lime : color.red, 20), 
         textcolor=color.white, 
         style=wasLong ? label.style_label_down : label.style_label_up, 
         size=size.normal)

// ==================== TABLE ====================
var table infoTable = table.new(position.top_right, 3, 11, bgcolor=color.new(color.black, 10), 
     frame_color=color.blue, frame_width=2, border_color=color.gray, border_width=1)

if barstate.islast
    // Header
    table.cell(infoTable, 0, 0, "PRO SIMPLE", text_color=color.white, bgcolor=color.new(color.blue, 30), text_size=size.normal)
    table.cell(infoTable, 1, 0, "VALUE", text_color=color.white, bgcolor=color.new(color.blue, 30), text_size=size.normal)
    table.cell(infoTable, 2, 0, "STATUS", text_color=color.white, bgcolor=color.new(color.blue, 30), text_size=size.normal)
    
    // Row 1: Trend
    table.cell(infoTable, 0, 1, "TREND", text_color=color.white, text_size=size.small)
    trendValue = e20 > e200 ? "+" + str.tostring((e20/e200 - 1) * 100, "#.#") + "%" : str.tostring((e20/e200 - 1) * 100, "#.#") + "%"
    table.cell(infoTable, 1, 1, trendValue, text_color=trendColor, text_size=size.small)
    table.cell(infoTable, 2, 1, trendStatus, text_color=trendColor, text_size=size.small)
    
    // Row 2: RSI
    table.cell(infoTable, 0, 2, "RSI(14)", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 2, str.tostring(rsi, "#.#"), text_color=rsiColor, text_size=size.small)
    table.cell(infoTable, 2, 2, rsiStatus, text_color=rsiColor, text_size=size.small)
    
    // Row 3: MACD
    table.cell(infoTable, 0, 3, "MACD", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 3, str.tostring(hist, "#.##"), text_color=macdColor, text_size=size.small)
    table.cell(infoTable, 2, 3, macdStatus, text_color=macdColor, text_size=size.small)
    
    // Row 4: Setup
    table.cell(infoTable, 0, 4, "SETUP", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 4, buySetup or sellSetup ? "●" : "○", text_color=setupColor, text_size=size.large)
    table.cell(infoTable, 2, 4, setupStatus, text_color=setupColor, text_size=size.small)
    
    // Row 5: Candle
    table.cell(infoTable, 0, 5, "CANDLE", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 5, candleStatus, text_color=bullCandle ? color.lime : color.red, text_size=size.small)
    table.cell(infoTable, 2, 5, bullCandle ? "↑" : "↓", text_color=bullCandle ? color.lime : color.red, text_size=size.normal)
    
    // Row 6: Last Signal
    table.cell(infoTable, 0, 6, "LAST SIGNAL", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 6, lastSignalType, text_color=lastSignalColor, text_size=size.small)
    table.cell(infoTable, 2, 6, str.tostring(lastSignalBars) + " bars ago", text_color=color.gray, text_size=size.small)
    
    // Row 7: ATR
    table.cell(infoTable, 0, 7, "ATR", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 7, str.tostring(atr, format.mintick), text_color=color.yellow, text_size=size.small)
    table.cell(infoTable, 2, 7, "Volatility", text_color=color.gray, text_size=size.small)
    
    // Separator
    table.cell(infoTable, 0, 8, "━━━━━━━━━━━━━━━━", text_color=color.gray, text_size=size.small)
    table.merge_cells(infoTable, 0, 8, 2, 8)
    
    // Row 8: Position
    table.cell(infoTable, 0, 9, "POSITION", text_color=color.white, text_size=size.small)
    pnlText = inTrade ? (positionPnL > 0 ? "+" : "") + str.tostring(positionPnL, "#.##") + "%" : "-"
    table.cell(infoTable, 1, 9, pnlText, text_color=positionColor, text_size=size.small)
    table.cell(infoTable, 2, 9, "R:R " + (inTrade ? str.tostring(riskRewardRatio, "#.#") : "-"), text_color=color.gray, text_size=size.small)
    
    // Row 9: Status
    table.cell(infoTable, 0, 10, "STATUS", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 10, positionStatus, text_color=inTrade ? color.orange : color.gray, text_size=size.small)
    table.cell(infoTable, 2, 10, inTrade ? tradeType : "-", text_color=tradeType == "LONG" ? color.lime : tradeType == "SHORT" ? color.red : color.gray, text_size=size.small)

// ==================== UNIFIED ALERT ====================
// Combine all alert conditions into one
anyAlert = buySignal or sellSignal or alertTP1Long or alertTP2Long or alertSLLong or 
           alertTP1Short or alertTP2Short or alertSLShort or alertTrailLong or alertTrailShort or
           exitLong or exitShort

alertcondition(anyAlert, "🔔 PRO TRADER ALERT", 
     "{{ticker}} - {{interval}}\n" +
     "Price: {{close}}\n" +
     "Time: {{timenow}}\n\n" +
     "Check your chart for signal details!")

// Plot RSI invisibly for reference
plot(rsi, "RSI", display=display.none)

// Reset alert flags
if barstate.isconfirmed
    alertTP1Long := false
    alertTP2Long := false
    alertSLLong := false
    alertTP1Short := false
    alertTP2Short := false
    alertSLShort := false
    alertTrailLong := false
    alertTrailShort := false