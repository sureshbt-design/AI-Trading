# PATCC Enterprise

## Developer Guide

Version: 0.7

Author: Suresh Thumma & ChatGPT

Project: Personal AI Trading & Capital Command Center (PATCC)

---

# Purpose

PATCC is a modular, enterprise-style platform that helps make better financial decisions by combining:

- Market Intelligence

- Technical Analysis

- Portfolio Monitoring

- Retirement Planning

- Investment Research

- AI-assisted Decision Support

The project is designed for long-term maintainability and extensibility.

---

# Development Philosophy

PATCC follows these principles:

1. Build production-quality code.

2. Keep modules independent.

3. Configuration over hardcoding.

4. Test every feature before committing.

5. Commit only working code.

6. Tag stable releases.

7. Document important architectural decisions.

---

# Project Structure

PATCC/

    Agents/

    Config/

    Core/

    Data/

    Docs/

    Indicators/

    Logs/

    Models/

    Providers/

    Reports/

    Scripts/

    Services/

    Tests/

    Utils/

    [main.py](http://main.py)

Each folder has one responsibility.

---

# Starting PATCC

Always start development using:

```powershell

.\start_patcc.ps1

```

The startup script performs:

- Virtual environment activation

- Git status check

- Python version verification

- PATCC startup test

If the script completes successfully, development can begin.

---

# Virtual Environment

PATCC uses a dedicated Python virtual environment.

Location

```

C:\AI-Trading\.venv

```

Activate manually if necessary:

```powershell

.\.venv\Scripts\Activate.ps1

```

Verify:

```powershell

python --version

pip --version

```

The PowerShell prompt should display:

```

(.venv)

```

---

# Git Workflow

Daily development process

1. Start PATCC

```powershell

.\start_patcc.ps1

```

2. Verify repository

```powershell

git status

```

3. Develop

4. Test

```powershell

python 01-Projects\PATCC\[main.py](http://main.py)

```

5. Commit

```powershell

git add .

git commit -m "meaningful message"

```

6. Push

```powershell

git push

```

7. Tag stable versions

```powershell

git tag version-name

git push origin version-name

```

---

# Providers

PATCC supports multiple data providers.

Current

✓ Yahoo Finance

Future

• Interactive Brokers

• Schwab

• Coinbase

• Polygon

• Finnhub

Providers should never contain business logic.

They only download data.

---

# Data Service

The Data Service is the single gateway for market data.

Other modules should NEVER communicate directly with providers.

Correct

Scanner

↓

DataService

↓

Provider

Incorrect

Scanner

↓

YahooProvider

---

# Cache Service

Purpose

Reduce downloads.

Increase speed.

Prevent unnecessary API calls.

Cached data is stored under

```

Data/cache/

```

Cache files are ignored by Git.

---

# Watchlists

Watchlists are stored as JSON.

```

Data/Watchlists/

```

Examples

macro_markets.json

core_etfs.json

us_day_trading.json

crypto_core.json

To add a new watchlist:

1. Create JSON file

2. Restart PATCC

UniverseManager loads automatically.

No Python code changes required.

---

# Coding Standards

Use

- Classes

- Dataclasses

- Type hints

- Small functions

- Clear variable names

Avoid

- Duplicate code

- Hardcoded paths

- Global variables

---

# Release Process

Development

↓

Testing

↓

Git Commit

↓

Git Push

↓

Git Tag

↓

Stable Release

Never tag unstable code.

---

# Troubleshooting

Problem

ModuleNotFoundError

Solution

Activate virtual environment.

---

Problem

Git reports modified cache files.

Solution

Verify .gitignore.

---

Problem

JSON parsing error.

Solution

Validate using

python -m json.tool filename.json

---

Problem

Import error

Solution

Verify package structure and **init**.py files.

---

# Long-Term Vision

PATCC is intended to become an enterprise-quality financial decision platform capable of:

- Market analysis

- Technical scanning

- Portfolio management

- Risk management

- Retirement planning

- Tax-aware investing

- AI-assisted decision support

The architecture should remain modular and maintainable as new capabilities are added.