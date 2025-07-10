
# GitHub Copilot Repository Custom Instructions

## 📌 Project Overview
This is a Python-based automated trading bot for FOREX markets, focused on scalping and day trading. The project is modular, designed with maintainability, risk control, and performance tracking in mind. It integrates MetaTrader 5 for trade execution and Telegram for signal notifications.

## 🧠 What Copilot should know about this repository

- The project uses Python 3.10+.
- Key libraries include: `MetaTrader5`, `telebot`, `dotenv`, `pandas`, `numpy`.
- MT5 API is used to connect, analyze, and execute orders.
- Signals are generated based on technical indicators (EMA, RSI, ATR, ADX, candlestick patterns).
- Risk management is based on account balance percentage and ATR-based SL/TP.
- The bot structure is modular: `main.py`, `mt5_connector.py`, `signal_generator.py`, `telegram_alerts.py`, `risk_manager.py`.
- We use `.env` for sensitive data and `.log` files for operational logs.
- Style guide: PEP8, type hints are preferred, and all functions must have docstrings.
- Testing: `pytest` is used for functional testing.

## ✅ How Copilot can help

- Generate functions with clear and complete docstrings.
- Suggest unit tests with edge cases using `pytest`.
- Automatically infer signal conditions based on indicator input.
- Propose well-documented helper utilities (e.g., ATR calculator, RSI crossover detector).
- Help create and update documentation and README.
- Avoid suggesting hardcoded credentials or tokens.
- Respect environment variable usage for secrets and configs.
- Propose logging instead of `print()` for traceability.

## 🛑 What Copilot should avoid

- Do not suggest hardcoding passwords, API keys, or tokens.
- Do not remove `.env` references in favor of inline credentials.
- Avoid writing code that lacks typing or documentation.
- Do not suggest synchronous code for asynchronous operations (like Telegram messaging if async is implemented).
- Avoid suggesting non-PEP8-compliant code unless explicitly required.

## 🧪 Testing and Quality Expectations

- Suggest test cases for all new functions using `pytest`.
- Prefer high-cohesion, low-coupling code.
- Ensure all signals and execution logic are deterministic and testable.

## 🧼 Formatting, Commits, and Pull Requests

- Code must be formatted with `black` and follow PEP8.
- Commits should use present tense: `Add risk management`, `Fix signal logic`.
- Pull requests must include a brief description, checklist, and pass tests.

