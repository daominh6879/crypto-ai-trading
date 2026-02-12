@echo off
echo ========================================
echo   CRYPTO AI TRADING - HISTORICAL ANALYSIS
echo ========================================
echo.
echo Running comprehensive backtest analysis...
echo This will test the system across multiple years
echo.

python main.py --mode historical --symbol BTCUSDT --start-year 2017 --end-year 2025

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Analysis completed successfully!
) else (
    echo.
    echo ❌ Analysis failed with error code %ERRORLEVEL%
)

echo.
echo Press any key to exit...
pause >nul