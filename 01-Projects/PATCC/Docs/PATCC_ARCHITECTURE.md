# PATCC Architecture

## Purpose

PATCC is a Personal AI Trading & Capital Command Center designed to support market analysis, trading decisions, portfolio monitoring, and long-term financial planning.

## Core Architecture

```text

External Providers

    |

    v

Provider Layer

    |

    v

Data Service

    |

    v

MarketData Model

    |

    v

Indicators

    |

    v

Trend / Momentum / Volatility Analysis

    |

    v

Scanner Engine

    |

    v

Scoring Engine

    |

    v

AI Decision Engine

    |

    v

Daily Executive Brief

## Main Packages

### Config

Stores global configuration.

### Providers

Connects to external data sources such as Yahoo, IBKR, Coinbase, Schwab, and future providers.

### Services

Provides shared business services such as market data and caching.

### Models

Stores shared dataclasses such as MarketData, Universe, and TrendSignal.

### Indicators

Contains reusable technical indicators such as EMA, SMA, RSI, ATR, MACD, ADX, VWAP, and Relative Volume.

### Core

Contains main business logic such as UniverseManager, MarketStateEngine, and TrendAnalyzer.

### Data

Stores watchlists, cache, and future local datasets.

### Docs

Stores project documentation.

### Tests

Stores test scripts for validating indicators, services, and engines.

## Data Flow

1. A module requests data from DataService.
2. DataService checks CacheService.
3. If cache is valid, cached MarketData is returned.
4. If cache is expired or missing, DataService calls the provider.
5. Provider returns raw data.
6. DataService wraps the raw data in MarketData.
7. Indicators calculate values from MarketData.
8. Analyzer modules interpret indicator values.
9. Scanner and scoring engines rank opportunities.
10. Reports summarize results.

## Provider Strategy

Current provider:

- YahooProvider

Planned providers:

- IBKRProvider
- CoinbaseProvider
- SchwabProvider
- PolygonProvider
- FinnhubProvider

Long-term design:

Primary Provider

    |

Fallback Provider

    |

Cached Data

## Asset Classes

PATCC is designed to support:

- US stocks
- US ETFs
- Indexes
- Precious metals
- Base metals
- Oil and energy
- Energy stocks and ETFs
- Crypto
- Indian equities
- Bonds and treasury indicators
- Macro indicators

## Sprint 008 Focus

Sprint 008 builds the Technical Analysis Engine.

Completed:

- BaseIndicator
- EMA
- SMA
- RSI
- TrendAnalyzer
- MarketData model

Next:

- ATR
- MACD
- ADX
- Relative Volume
- VWAP

```

```

```

```

