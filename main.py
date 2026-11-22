
from flask import Flask, request, redirect, render_template_string
from database import (
    create_database,
    get_stocks,
    save_stock,
    update_stock,
    delete_stock
)
import math
import re
import time
import yfinance as yf

app = Flask(__name__)
create_database()

# Cache stock information for five minutes
price_cache = {}
history_cache = {}
company_name_cache = {}
CACHE_SECONDS = 300


# Get the latest available closing price
def get_current_price(symbol):
    now = time.time()

    if symbol in price_cache:
        saved_time, price, date = price_cache[symbol]
        if now - saved_time < CACHE_SECONDS:
            return price, date

    try:
        history = yf.Ticker(symbol).history(
            period="5d",
            interval="1d",
            auto_adjust=False,
            timeout=8
        )

        if history.empty:
            return None, None

        price = float(history.iloc[-1]["Close"])

        if not math.isfinite(price) or price <= 0:
            return None, None

        date = history.index[-1].strftime("%b %d, %Y")
        price_cache[symbol] = (now, price, date)

        return price, date

    except Exception as error:
        print(f"Price error for {symbol}: {error}")
        return None, None


# Get the company name
def get_company_name(symbol):
    now = time.time()

    if symbol in company_name_cache:
        saved_time, name = company_name_cache[symbol]
        if now - saved_time < 86400:
            return name

    try:
        info = yf.Ticker(symbol).info

        name = (
            info.get("longName")
            or info.get("shortName")
            or symbol
        )

        company_name_cache[symbol] = (now, name)
        return name

    except Exception as error:
        print(f"Company name error for {symbol}: {error}")
        return symbol


# Get historical stock prices
def get_price_history(symbol, period):
    periods = {
        "1w": ("5d", "1d"),
        "1m": ("1mo", "1d"),
        "1y": ("1y", "1wk")
    }

    if period not in periods:
        period = "1m"

    cache_key = (symbol, period)
    now = time.time()

    if cache_key in history_cache:
        saved_time, dates, prices = history_cache[cache_key]
        if now - saved_time < CACHE_SECONDS:
            return dates, prices

    try:
        yf_period, interval = periods[period]

        history = yf.Ticker(symbol).history(
            period=yf_period,
            interval=interval,
            auto_adjust=False,
            timeout=8
        )

        dates = []
        prices = []

        for date, row in history.iterrows():
            price = float(row["Close"])

            if math.isfinite(price) and price > 0:
                dates.append(date.strftime("%b %d, %Y"))
                prices.append(round(price, 2))

        history_cache[cache_key] = (now, dates, prices)
        return dates, prices

    except Exception as error:
        print(f"History error for {symbol}: {error}")
        return [], []


@app.route("/")
def home():
    stocks = get_stocks()
    portfolio = []

    total_invested = 0
    total_current = 0
    total_shares = 0
    all_prices_available = True
    breakdown = {}

    for stock in stocks:
        symbol = stock["symbol"]
        shares = stock["shares"]
        purchase_price = stock["price"]

        original_value = shares * purchase_price
        current_price, price_date = get_current_price(symbol)

        current_value = None
        gain_loss = None
        gain_percent = None

        if current_price is not None:
            current_value = shares * current_price
            gain_loss = current_value - original_value
            gain_percent = (
                gain_loss / original_value * 100
                if original_value > 0 else 0
            )
            total_current += current_value
        else:
            all_prices_available = False

        total_invested += original_value
        total_shares += shares

        breakdown[symbol] = (
            breakdown.get(symbol, 0) + original_value
        )

        portfolio.append({
            "id": stock["id"],
            "symbol": symbol,
            "company_name": get_company_name(symbol),
            "shares": shares,
            "price": purchase_price,
            "original_value": original_value,
            "current_price": current_price,
            "current_value": current_value,
            "gain_loss": gain_loss,
            "gain_percent": gain_percent,
            "price_date": price_date
        })

    stocks_tracked = len(breakdown)

    if stocks and all_prices_available:
        total_gain = total_current - total_invested
        total_gain_percent = (
            total_gain / total_invested * 100
            if total_invested > 0 else 0
        )
    else:
        total_current = None
        total_gain = None
        total_gain_percent = None

    available_symbols = list(breakdown.keys())

    selected_symbol = request.args.get(
        "symbol",
        available_symbols[0] if available_symbols else ""
    ).upper()

    if selected_symbol not in available_symbols:
        selected_symbol = (
            available_symbols[0] if available_symbols else ""
        )

    selected_period = request.args.get("period", "1m")

    if selected_period not in ("1w", "1m", "1y"):
        selected_period = "1m"

    history_dates = []
    history_prices = []

    if selected_symbol:
        history_dates, history_prices = get_price_history(
            selected_symbol, selected_period
        )

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>PSDA | Investment Dashboard</title>

    <style>
        :root {
            --background: #0b1120;
            --sidebar: #0f172a;
            --card: #151f32;
            --card-hover: #1b2940;
            --border: #29364c;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --blue: #3b82f6;
            --green: #34d399;
            --red: #fb7185;
        }

        * {
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            margin: 0;
            background: var(--background);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
            line-height: 1.5;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        .layout {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar */

        .sidebar {
            width: 240px;
            background: var(--sidebar);
            border-right: 1px solid var(--border);
            padding: 28px 18px;
            flex-shrink: 0;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 0 12px 30px;
        }

        .brand-icon {
            background: var(--blue);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 23px;
            font-weight: bold;
        }

        .brand-name {
            font-size: 22px;
            font-weight: bold;
        }

        .brand-subtitle {
            font-size: 11px;
            color: var(--muted);
        }

        .nav-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--muted);
            padding: 0 12px;
            margin: 20px 0 12px;
        }

        .nav-link {
            display: block;
            padding: 13px 15px;
            border-radius: 9px;
            margin-bottom: 6px;
            font-size: 14px;
            color: var(--muted);
        }

        .nav-link:hover,
        .nav-link.active {
            background: #1e3354;
            color: #93c5fd;
        }

        .sidebar-note {
            margin-top: 45px;
            padding: 15px;
            background: #17243a;
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--muted);
            font-size: 12px;
        }

        /* Main content */

        .main {
            flex: 1;
            min-width: 0;
            padding: 32px;
            max-width: 1600px;
            margin: 0 auto;
        }

        .page-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 15px;
            margin-bottom: 32px;
            flex-wrap: wrap;
        }

        .page-header h1 {
            margin: 0 0 6px;
            font-size: 29px;
            letter-spacing: -0.6px;
        }

        .page-header p {
            margin: 0;
            color: var(--muted);
            font-size: 14px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #12352e;
            color: var(--green);
            border: 1px solid #225a4b;
            padding: 9px 13px;
            border-radius: 30px;
            font-size: 12px;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            background: var(--green);
            border-radius: 50%;
        }

        .section-title {
            font-size: 19px;
            margin: 30px 0 16px;
            font-weight: 600;
        }

        /* Summary cards */

        .stats {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
        }

        .stat-card,
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
        }

        .stat-card {
            padding: 24px;
            min-width: 0;
        }

        .stat-label {
            font-size: 13px;
            color: var(--muted);
            margin-bottom: 12px;
        }

        .stat-value {
            font-size: 29px;
            font-weight: bold;
            letter-spacing: -0.5px;
            overflow-wrap: anywhere;
        }

        .stat-description {
            color: var(--muted);
            font-size: 12px;
            margin-top: 9px;
        }

        .positive {
            color: var(--green) !important;
        }

        .negative {
            color: var(--red) !important;
        }

        /* Shared cards */

        .card {
            padding: 25px;
            margin-bottom: 20px;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 22px;
        }

        .card h2 {
            margin: 0 0 5px;
            font-size: 19px;
        }

        .card-description {
            color: var(--muted);
            font-size: 13px;
            margin: 0;
        }

        /* Forms */

        .add-form,
        .history-controls {
            display: flex;
            align-items: end;
            gap: 14px;
            flex-wrap: wrap;
        }

        .field {
            flex: 1;
            min-width: 160px;
        }

        .field label {
            display: block;
            font-size: 12px;
            color: var(--muted);
            margin-bottom: 8px;
        }

        input,
        select {
            width: 100%;
            min-width: 0;
            padding: 12px;
            border: 1px solid #334155;
            border-radius: 8px;
            background: #0f172a;
            color: var(--text);
            font-size: 14px;
        }

        input::placeholder {
            color: #64748b;
        }

        input:focus,
        select:focus {
            outline: 2px solid var(--blue);
            border-color: var(--blue);
        }

        button {
            border: none;
            background: var(--blue);
            color: white;
            padding: 12px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            white-space: nowrap;
        }

        button:hover {
            filter: brightness(1.12);
        }

        .btn-remove {
            background: #43212d;
            color: #fda4af;
            border: 1px solid #753244;
        }

        /* Stock cards */

        .stock-list {
            display: grid;
            gap: 15px;
        }

        .stock-card {
            background: #101a2b;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 22px;
        }

        .stock-card:hover {
            border-color: #3b4e6b;
        }

        .stock-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            padding-bottom: 18px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }

        .company-name {
            font-size: 18px;
            font-weight: bold;
        }

        .ticker {
            display: inline-block;
            background: #243752;
            color: #93c5fd;
            border-radius: 5px;
            padding: 3px 9px;
            margin-top: 8px;
            font-size: 12px;
            font-weight: bold;
        }

        .price-date {
            font-size: 12px;
            color: var(--muted);
        }

        .stock-details {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 20px;
        }

        .detail {
            min-width: 0;
        }

        .detail-label {
            display: block;
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 9px;
        }

        .detail-value {
            font-size: 19px;
            font-weight: bold;
            overflow-wrap: anywhere;
        }

        .stock-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 22px;
            padding-top: 18px;
            border-top: 1px solid var(--border);
        }

        .stock-actions form {
            margin: 0;
        }

        /* Charts */

        .chart-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr);
            gap: 20px;
        }

        .history-controls {
            margin-bottom: 20px;
        }

        .history-controls .field {
            max-width: 200px;
        }

        .history-chart {
            position: relative;
            height: 330px;
            width: 100%;
        }

        .donut-chart {
            position: relative;
            height: 330px;
            max-width: 400px;
            margin: auto;
        }

        .empty {
            padding: 30px;
            text-align: center;
            color: var(--muted);
            background: #101a2b;
            border-radius: 10px;
        }

        .note {
            font-size: 12px;
            color: var(--muted);
            line-height: 1.8;
        }

        footer {
            margin: 25px 0;
        }

        /* Responsive layout */

        @media (max-width: 1150px) {
            .chart-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 900px) {
            .sidebar {
                width: 190px;
            }

            .main {
                padding: 24px;
            }

            .stats {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 700px) {
            .layout {
                display: block;
            }

            .sidebar {
                width: 100%;
                padding: 15px;
                border-right: none;
                border-bottom: 1px solid var(--border);
            }

            .brand {
                padding-bottom: 10px;
            }

            .nav-title,
            .sidebar-note {
                display: none;
            }

            .sidebar nav {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .nav-link {
                margin: 0;
                padding: 9px 12px;
            }

            .main {
                padding: 18px 12px;
            }

            .page-header h1 {
                font-size: 24px;
            }

            .stock-details {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .card {
                padding: 18px;
            }
        }

        @media (max-width: 480px) {
            .stats,
            .stock-details {
                grid-template-columns: 1fr;
            }

            .stat-value {
                font-size: 25px;
            }

            .field,
            .history-controls .field {
                width: 100%;
                max-width: none;
            }

            .history-chart {
                height: 260px;
            }
        }
    </style>
</head>

<body>

<div class="layout">

    <!-- SIDEBAR -->
    <aside class="sidebar">

        <div class="brand">
            <div class="brand-icon">P</div>
            <div>
                <div class="brand-name">PSDA</div>
                <div class="brand-subtitle">
                    Stock Portfolio Tracker
                </div>
            </div>
        </div>

        <nav>
            <div class="nav-title">Navigation</div>

            <a href="#overview" class="nav-link active">
                ◫ &nbsp; Dashboard
            </a>

            <a href="#portfolio" class="nav-link">
                ▤ &nbsp; My Portfolio
            </a>

            <a href="#history" class="nav-link">
                ↗ &nbsp; Price History
            </a>

            <a href="#breakdown" class="nav-link">
                ◉ &nbsp; Breakdown
            </a>
        </nav>

        <div class="sidebar-note">
            <strong style="color: #f1f5f9;">
                About PSDA
            </strong>

            <p>
                A simple application for tracking
                investments you already own.
            </p>

            <p style="margin-bottom: 0;">
                Educational use only.
            </p>
        </div>

    </aside>

    <!-- MAIN DASHBOARD -->
    <main class="main">

        <div class="page-header" id="overview">
            <div>
                <h1>Portfolio Dashboard</h1>
                <p>
                    Track your investments in one place.
                </p>
            </div>

            <div class="status-pill">
                <span class="status-dot"></span>
                Latest Available Prices
            </div>
        </div>

        <!-- PORTFOLIO SUMMARY -->
        <h2 class="section-title">Portfolio Overview</h2>

        <div class="stats">

            <div class="stat-card">
                <div class="stat-label">
                    Total Originally Invested
                </div>

                <div class="stat-value">
                    ${{ "{:,.2f}".format(total_invested) }}
                </div>

                <div class="stat-description">
                    Your original investment
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    Current Portfolio Value
                </div>

                <div class="stat-value">
                    {% if total_current is not none %}
                        ${{ "{:,.2f}".format(total_current) }}
                    {% else %}
                        Unavailable
                    {% endif %}
                </div>

                <div class="stat-description">
                    Based on latest available prices
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    Total Gain / Loss
                </div>

                {% if total_gain is not none %}
                    <div class="stat-value
                        {{ 'positive' if total_gain >= 0 else 'negative' }}">
                        {{ '+' if total_gain >= 0 else '-' }}${{
                            "{:,.2f}".format(total_gain|abs)
                        }}
                    </div>

                    <div class="stat-description
                        {{ 'positive' if total_gain_percent >= 0 else 'negative' }}">
                        {{ "%+.2f"|format(total_gain_percent) }}%
                        overall return
                    </div>
                {% else %}
                    <div class="stat-value">
                        Unavailable
                    </div>
                {% endif %}
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    Total Shares
                </div>

                <div class="stat-value">
                    {{ total_shares }}
                </div>

                <div class="stat-description">
                    Shares in your portfolio
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    Stocks Tracked
                </div>

                <div class="stat-value">
                    {{ stocks_tracked }}
                </div>

                <div class="stat-description">
                    Different stock symbols
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-label">
                    Market Data
                </div>

                <div class="stat-value"
                     style="font-size: 19px;">
                    Daily Closing Prices
                </div>

                <div class="stat-description">
                    Refresh to check for updates
                </div>
            </div>

        </div>

        <!-- ADD STOCK -->
        <h2 class="section-title" id="portfolio">
            My Portfolio
        </h2>

        <div class="card">

            <div class="card-header">
                <div>
                    <h2>Add an Existing Stock</h2>
                    <p class="card-description">
                        Enter details of a stock you already own.
                    </p>
                </div>
            </div>

            <form class="add-form"
                  action="/add"
                  method="POST">

                <div class="field">
                    <label for="new-symbol">
                        Stock Symbol
                    </label>

                    <input
                        id="new-symbol"
                        name="symbol"
                        type="text"
                        placeholder="e.g. AAPL"
                        required
                    >
                </div>

                <div class="field">
                    <label for="new-shares">
                        Shares Owned
                    </label>

                    <input
                        id="new-shares"
                        name="shares"
                        type="number"
                        min="1"
                        step="1"
                        placeholder="e.g. 5"
                        required
                    >
                </div>

                <div class="field">
                    <label for="new-price">
                        Original Price Per Share
                    </label>

                    <input
                        id="new-price"
                        name="price"
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="e.g. 180"
                        required
                    >
                </div>

                <button type="submit">
                    + Add Stock
                </button>

            </form>
        </div>

        <!-- SAVED STOCKS -->
        <div class="card">

            <div class="card-header">
                <div>
                    <h2>Your Holdings</h2>
                    <p class="card-description">
                        View and manage your existing investments.
                    </p>
                </div>
            </div>

            {% if portfolio %}

                <div class="stock-list">

                {% for stock in portfolio %}

                    <div class="stock-card">

                        <div class="stock-header">

                            <div>
                                <div class="company-name">
                                    {{ stock.company_name }}
                                </div>

                                <span class="ticker">
                                    {{ stock.symbol }}
                                </span>
                            </div>

                            <div class="price-date">
                                Price Date:
                                {{ stock.price_date or 'Unavailable' }}
                            </div>

                        </div>

                        <div class="stock-details">

                            <div class="detail">
                                <label class="detail-label">
                                    Shares Owned
                                </label>

                                <input
                                    type="number"
                                    name="shares"
                                    form="edit-{{ stock.id }}"
                                    value="{{ stock.shares }}"
                                    min="1"
                                    step="1"
                                    required
                                >
                            </div>

                            <div class="detail">
                                <label class="detail-label">
                                    Original Price Per Share
                                </label>

                                <input
                                    type="number"
                                    name="price"
                                    form="edit-{{ stock.id }}"
                                    value="{{ '%.2f'|format(stock.price) }}"
                                    min="0.01"
                                    step="0.01"
                                    required
                                >
                            </div>

                            <div class="detail">
                                <span class="detail-label">
                                    Original Value
                                </span>

                                <div class="detail-value">
                                    ${{ "{:,.2f}".format(stock.original_value) }}
                                </div>
                            </div>

                            <div class="detail">
                                <span class="detail-label">
                                    Current Price Per Share
                                </span>

                                <div class="detail-value">
                                    {% if stock.current_price is not none %}
                                        ${{ "{:,.2f}".format(stock.current_price) }}
                                    {% else %}
                                        N/A
                                    {% endif %}
                                </div>
                            </div>

                            <div class="detail">
                                <span class="detail-label">
                                    Current Value
                                </span>

                                <div class="detail-value">
                                    {% if stock.current_value is not none %}
                                        ${{ "{:,.2f}".format(stock.current_value) }}
                                    {% else %}
                                        N/A
                                    {% endif %}
                                </div>
                            </div>

                            <div class="detail">
                                <span class="detail-label">
                                    Gain / Loss
                                </span>

                                <div class="detail-value">

                                    {% if stock.gain_loss is not none %}

                                        <span class="{{ 'positive' if stock.gain_loss >= 0 else 'negative' }}">
                                            {{ '+' if stock.gain_loss >= 0 else '-' }}${{
                                                "{:,.2f}".format(stock.gain_loss|abs)
                                            }}
                                        </span>

                                        <div style="font-size: 13px; margin-top: 5px;"
                                             class="{{ 'positive' if stock.gain_percent >= 0 else 'negative' }}">
                                            {{ "%+.2f"|format(stock.gain_percent) }}%
                                        </div>

                                    {% else %}
                                        N/A
                                    {% endif %}

                                </div>
                            </div>

                        </div>

                        <div class="stock-actions">

                            <form
                                id="edit-{{ stock.id }}"
                                action="/edit/{{ stock.id }}"
                                method="POST"
                            >
                                <button type="submit">
                                    Save Changes
                                </button>
                            </form>

                            <form
                                action="/delete/{{ stock.id }}"
                                method="POST"
                                onsubmit="return confirm('Remove this stock?');"
                            >
                                <button
                                    class="btn-remove"
                                    type="submit"
                                >
                                    Remove
                                </button>
                            </form>

                        </div>

                    </div>

                {% endfor %}

                </div>

            {% else %}

                <div class="empty">
                    No stocks added yet.
                    Add your first existing investment above.
                </div>

            {% endif %}

        </div>

        <!-- CHARTS -->
        <h2 class="section-title">
            Investment Charts
        </h2>

        <div class="chart-grid">

            <!-- PRICE HISTORY -->
            <div class="card" id="history">

                <div class="card-header">
                    <div>
                        <h2>Stock Price History</h2>
                        <p class="card-description">
                            View historical market prices.
                        </p>
                    </div>
                </div>

                {% if available_symbols %}

                    <form action="/#history"
                          method="GET"
                          class="history-controls">

                        <div class="field">
                            <label for="history-symbol">
                                Select Stock
                            </label>

                            <select
                                id="history-symbol"
                                name="symbol"
                            >
                                {% for symbol in available_symbols %}
                                    <option
                                        value="{{ symbol }}"
                                        {% if symbol == selected_symbol %}
                                            selected
                                        {% endif %}
                                    >
                                        {{ symbol }}
                                    </option>
                                {% endfor %}
                            </select>
                        </div>

                        <div class="field">
                            <label for="history-period">
                                Time Period
                            </label>

                            <select
                                id="history-period"
                                name="period"
                            >
                                <option value="1w"
                                    {% if selected_period == '1w' %}
                                        selected
                                    {% endif %}>
                                    1 Week
                                </option>

                                <option value="1m"
                                    {% if selected_period == '1m' %}
                                        selected
                                    {% endif %}>
                                    1 Month
                                </option>

                                <option value="1y"
                                    {% if selected_period == '1y' %}
                                        selected
                                    {% endif %}>
                                    1 Year
                                </option>
                            </select>
                        </div>

                        <button type="submit">
                            Show Chart
                        </button>

                    </form>

                    {% if history_prices %}

                        <h3 style="font-size: 15px; margin: 15px 0;">
                            {{ selected_symbol }} Price History
                        </h3>

                        <div class="history-chart">
                            <canvas id="historyChart"></canvas>
                        </div>

                        <p class="note">
                            Historical closing price per share.
                        </p>

                    {% else %}

                        <div class="empty">
                            Historical prices are unavailable.
                        </div>

                    {% endif %}

                {% else %}

                    <div class="empty">
                        Add a stock to view price history.
                    </div>

                {% endif %}

            </div>

            <!-- PORTFOLIO BREAKDOWN -->
            <div class="card" id="breakdown">

                <div class="card-header">
                    <div>
                        <h2>Portfolio Breakdown</h2>
                        <p class="card-description">
                            Your original investment allocation.
                        </p>
                    </div>
                </div>

                {% if total_invested > 0 %}

                    <div class="donut-chart">
                        <canvas id="portfolioChart"></canvas>
                    </div>

                {% else %}

                    <div class="empty">
                        Add stocks to view your breakdown.
                    </div>

                {% endif %}

            </div>

        </div>

        <footer>
            <p class="note">
                PSDA tracks existing investments only.
                It does not support buying or selling stocks.
                Market data may be delayed or unavailable.
                Historical charts show daily closing prices
                for week and month views and weekly closing
                prices for the year view.
                Gains and losses exclude dividends, fees,
                taxes, and stock-split adjustments to
                manually entered purchase costs.
                For educational use only.
            </p>
        </footer>

    </main>

</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
    const chartColors = [
        '#3b82f6',
        '#34d399',
        '#fbbf24',
        '#a78bfa',
        '#fb7185',
        '#22d3ee',
        '#f472b6',
        '#a3e635'
    ];

    const portfolioLabels = {{ chart_labels | tojson }};
    const portfolioValues = {{ chart_values | tojson }};

    const portfolioCanvas = document.getElementById(
        'portfolioChart'
    );

    if (portfolioCanvas && typeof Chart !== 'undefined') {
        new Chart(portfolioCanvas, {
            type: 'doughnut',

            data: {
                labels: portfolioLabels,
                datasets: [{
                    data: portfolioValues,
                    backgroundColor: portfolioLabels.map(
                        (_, i) => chartColors[i % chartColors.length]
                    ),
                    borderColor: '#151f32',
                    borderWidth: 4,
                    hoverOffset: 8
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',

                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#cbd5e1',
                            padding: 18,
                            usePointStyle: true
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce(
                                    (a, b) => a + b, 0
                                );

                                const percent = total > 0
                                    ? (context.parsed / total * 100).toFixed(1)
                                    : '0.0';

                                return context.label + ': $' +
                                    context.parsed.toLocaleString(
                                        'en-US',
                                        {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        }
                                    ) +
                                    ' (' + percent + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    const historyDates = {{ history_dates | tojson }};
    const historyPrices = {{ history_prices | tojson }};

    const historyCanvas = document.getElementById(
        'historyChart'
    );

    if (historyCanvas && typeof Chart !== 'undefined') {
        new Chart(historyCanvas, {
            type: 'line',

            data: {
                labels: historyDates,
                datasets: [{
                    label: {{ selected_symbol | tojson }} + ' Closing Price',
                    data: historyPrices,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(59, 130, 246, 0.12)',
                    borderWidth: 3,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#60a5fa'
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    intersect: false,
                    mode: 'index'
                },

                scales: {
                    x: {
                        grid: {
                            color: 'rgba(148, 163, 184, 0.07)'
                        },
                        ticks: {
                            color: '#94a3b8',
                            maxTicksLimit: 6,
                            maxRotation: 0
                        }
                    },

                    y: {
                        grid: {
                            color: 'rgba(148, 163, 184, 0.10)'
                        },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    }
                },

                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5e1'
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Price: $' +
                                    context.parsed.y.toFixed(2);
                            }
                        }
                    }
                }
            }
        });
    }
</script>

</body>
</html>
    """,
        portfolio=portfolio,
        total_invested=total_invested,
        total_current=total_current,
        total_gain=total_gain,
        total_gain_percent=total_gain_percent,
        total_shares=total_shares,
        stocks_tracked=stocks_tracked,
        chart_labels=list(breakdown.keys()),
        chart_values=list(breakdown.values()),
        available_symbols=available_symbols,
        selected_symbol=selected_symbol,
        selected_period=selected_period,
        history_dates=history_dates,
        history_prices=history_prices
    )


def valid_stock_values(shares, price):
    return (
        shares > 0
        and math.isfinite(price)
        and price > 0
    )


@app.route("/add", methods=["POST"])
def add_stock():
    symbol = request.form.get("symbol", "").strip().upper()

    try:
        shares = int(request.form["shares"])
        price = float(request.form["price"])
    except (ValueError, KeyError):
        return "Please enter valid numbers.", 400

    if (
        not re.fullmatch(r"[A-Z0-9^.-]{1,20}", symbol)
        or not valid_stock_values(shares, price)
    ):
        return "Please enter valid stock information.", 400

    save_stock(symbol, shares, price)
    return redirect("/")


@app.route("/edit/<int:stock_id>", methods=["POST"])
def edit_stock(stock_id):
    try:
        shares = int(request.form["shares"])
        price = float(request.form["price"])
    except (ValueError, KeyError):
        return "Please enter valid numbers.", 400

    if not valid_stock_values(shares, price):
        return "Please enter valid stock information.", 400

    update_stock(stock_id, shares, price)
    return redirect("/")


@app.route("/delete/<int:stock_id>", methods=["POST"])
def remove_stock(stock_id):
    delete_stock(stock_id)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5001)