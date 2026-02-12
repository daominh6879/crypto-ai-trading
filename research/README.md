# Research Archive

This directory contains analysis scripts, experimental code, and documentation from the trading system optimization project.

## Purpose

These files were used during the optimization process to:
- Analyze historical performance
- Test various improvement strategies
- Document findings and decisions
- Experiment with dynamic regime detection

**None of these files are required for production trading.** They are kept for reference and future research.

## Directory Structure

### `/analysis` - One-Time Analysis Scripts

Scripts used to analyze historical performance and find optimal parameters:

- **analyze_adx.py** - ADX distribution analysis that discovered the 20-30 "Goldilocks Zone"
- **deep_analysis_2022.py** - Comprehensive breakdown of 2022 bear market trades
- **analyze_long_trades_2022.py** - Individual long trade analysis in 2022
- **test_bear_market_improvements.py** - Tests of wider stops and other improvements
- **test_dynamic_regime_config.py** - Tests of complex regime detection system
- **test_simple_regime.py** - Tests of simple threshold-based regime detection

**Status**: Analysis complete. These scripts can be re-run on new data but are not needed for live trading.

### `/regime_detection` - Experimental Features (Not Implemented)

Regime detection systems that were tested but not implemented in production:

- **market_regime_detector.py** - Complex multi-factor regime detector
- **simple_regime_detector.py** - Simple threshold-based regime detector

**Status**: Tested and found to provide no improvement over ADX 20-30 filter. Not recommended for implementation.

**Why Not Implemented**:
- Disrupts trading system timing
- Made 2022 performance worse by -4.80%
- No advantage over simpler ADX 20-30 filter
- See documentation for full analysis

### `/documentation` - Analysis Reports & Findings

Comprehensive documentation of the optimization journey:

- **OPTIMIZATION_JOURNEY_COMPLETE.md** - Complete summary of entire optimization process
- **2022_DEEP_ANALYSIS_SUMMARY.md** - Detailed analysis of 2022 bear market performance
- **DYNAMIC_REGIME_CONFIG_ANALYSIS.md** - Original plan for dynamic regime detection
- **WHY_REGIME_DETECTION_FAILED.md** - Detailed explanation of why regime detection failed

**Recommended Reading Order**:
1. OPTIMIZATION_JOURNEY_COMPLETE.md (overview)
2. 2022_DEEP_ANALYSIS_SUMMARY.md (2022 details)
3. WHY_REGIME_DETECTION_FAILED.md (regime detection failure)

## Key Findings Summary

### What Worked ✓

**ADX 20-30 Filter** (Implemented in production)
- +21.67% combined improvement across 2022+2024
- 2022: -31.73% → -12.66% (+19.06% improvement)
- 2024: +18.33% → +20.93% (+2.60% improvement)
- Universal improvement with no trade-offs

### What Didn't Work ✗

**Dynamic Regime Detection** (Not implemented)
- Correctly detected market regimes
- But made performance worse by -4.80%
- Disrupted trading system timing
- No benefit over ADX filter

**Wider/Tighter Stops** (Not implemented)
- Created trade-offs (helps one market, hurts another)
- Net negative or neutral impact
- Current stops are optimal

## Production Implementation

The only change implemented in production code:

**config.py:**
```python
enable_regime_filter: bool = True  # ADX 20-30 filter enabled by default
```

**trading_system.py:**
- Added ADX 20-30 range filter to buy/sell conditions
- Filters out choppy (ADX < 20) and extreme (ADX > 30) conditions

## Can These Files Be Deleted?

**Analysis Scripts**: Can be deleted if disk space needed. All findings documented.

**Regime Detection**: Can be deleted. Not recommended for future use.

**Documentation**: Recommended to keep for reference and future optimization projects.

## Running Analysis Scripts

If you want to re-run any analysis:

```bash
# From project root
cd research/analysis

# Run ADX analysis
python analyze_adx.py

# Run 2022 deep analysis
python deep_analysis_2022.py

# Run long trade analysis
python analyze_long_trades_2022.py

# Test regime detection
python test_simple_regime.py
```

**Note**: Some scripts may take 5-15 minutes to run due to data fetching and backtesting.

## Future Research Ideas

If current performance (+8.27% combined) becomes insufficient:

1. **More Selective Long Filtering** - Filter by trade characteristics, not blanket disable
2. **Dynamic Position Sizing** - Adjust size based on ADX strength within 20-30 range
3. **Adaptive Exits** - Tighten trailing stops when ADX declining
4. **Monthly Regime Detection** - More granular than annual detection

See OPTIMIZATION_JOURNEY_COMPLETE.md for detailed descriptions.

---

**Created**: 2026-02-12
**Purpose**: Archive optimization research and analysis
**Status**: Complete - Production implementation finalized
