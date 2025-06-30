import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging

# Minimal version for reliable deployment
logging.basicConfig(level=logging.INFO)

def get_data_and_create_simple_dashboard():
    """Create a simple HTML dashboard with basic chart using only HTML/CSS/JS"""
    try:
        # Get S&P 500 data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)
        
        sp500 = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
        closes = sp500['Close'].dropna()
        
        # Calculate metrics
        ma_200 = closes.rolling(window=200).mean()
        std_200 = closes.rolling(window=200).std()
        
        current_price = closes.iloc[-1]
        current_ma = ma_200.iloc[-1]
        current_std = std_200.iloc[-1]
        std_away = (current_price - current_ma) / current_std
        
        # Get last 30 days for chart data
        last_30_days = closes.tail(30)
        ma_30_days = ma_200.tail(30)
        
        # Convert to lists for JavaScript
        dates = [d.strftime('%Y-%m-%d') for d in last_30_days.index]
        prices = last_30_days.tolist()
        mas = ma_30_days.tolist()
        
        # Determine status
        abs_std = abs(std_away)
        if 2.0 <= abs_std <= 3.0:
            status = "🚨 ALERT"
            status_color = "#ff4444"
        elif abs_std < 2.0:
            status = "✅ NORMAL"
            status_color = "#44ff44"
        else:
            status = "⚠️ EXTREME"
            status_color = "#ff8800"
        
        direction = "above" if std_away > 0 else "below"
        
        # Create HTML with embedded Chart.js
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S&P 500 Monitor</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .status {{
            font-size: 1.8em;
            font-weight: bold;
            color: {status_color};
            margin: 15px 0;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-title {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .chart-container {{
            padding: 30px;
            background: white;
        }}
        .chart-wrapper {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        .info {{
            padding: 30px;
            background: #f8f9fa;
            line-height: 1.6;
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            border-radius: 0 0 10px 10px;
        }}
        @media (max-width: 768px) {{
            .metrics {{ grid-template-columns: 1fr; }}
            .chart-wrapper {{ height: 300px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>S&P 500 Standard Deviation Monitor</h1>
            <div class="status">{status}</div>
            <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-title">Current Price</div>
                <div class="metric-value">${current_price:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">200-Day Average</div>
                <div class="metric-value">${current_ma:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Standard Deviations</div>
                <div class="metric-value" style="color: {status_color};">{std_away:.2f}σ</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Direction</div>
                <div class="metric-value">{direction.title()}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>S&P 500 Price vs 200-Day Moving Average (Last 30 Days)</h2>
            <div class="chart-wrapper">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
        
        <div class="info">
            <h3>Understanding the Analysis</h3>
            <p><strong>Current Status:</strong> The S&P 500 is <strong>{abs_std:.2f} standard deviations {direction}</strong> its 200-day moving average.</p>
            
            <div style="margin: 20px 0;">
                <p><strong>Status Meanings:</strong></p>
                <ul>
                    <li><span style="color: #44ff44; font-weight: bold;">✅ NORMAL (< 2σ):</span> Price within typical range</li>
                    <li><span style="color: #ff4444; font-weight: bold;">🚨 ALERT (2-3σ):</span> Unusual conditions - potential opportunity or risk</li>
                    <li><span style="color: #ff8800; font-weight: bold;">⚠️ EXTREME (> 3σ):</span> Very rare conditions - significant market event</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Data: Yahoo Finance | Updated hourly during market hours | For informational purposes only</p>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('priceChart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: 'S&P 500 Price',
                    data: {prices},
                    borderColor: '#000000',
                    backgroundColor: 'rgba(0,0,0,0.1)',
                    borderWidth: 2,
                    tension: 0,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }}, {{
                    label: '200-Day Moving Average',
                    data: {mas},
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37,99,235,0.1)',
                    borderWidth: 2,
                    tension: 0,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: false,
                        grid: {{
                            color: 'rgba(0,0,0,0.1)'
                        }},
                        title: {{
                            display: true,
                            text: 'Price ($)'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: 'rgba(0,0,0,0.1)'
                        }},
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                hover: {{
                    mode: 'index',
                    intersect: false
                }}
            }}
        }});
    </script>
</body>
</html>
        """
        
        # Save the HTML file
        with open('sp500_dashboard.html', 'w') as f:
            f.write(html_content)
        
        # Save JSON data
        data_json = {
            'timestamp': datetime.now().isoformat(),
            'current_price': float(current_price),
            'ma_200': float(current_ma),
            'std_200': float(current_std),
            'std_away': float(std_away),
            'status': status,
            'direction': direction,
            'alert': 2.0 <= abs_std <= 3.0
        }
        
        with open('sp500_data.json', 'w') as f:
            json.dump(data_json, f, indent=2)
        
        logging.info("Simple dashboard created successfully!")
        logging.info(f"Status: {status} | Price: ${current_price:.2f} | σ: {std_away:.2f}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error creating dashboard: {e}")
        
        # Create error page
        error_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>S&P 500 Monitor - Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
        .error {{ background: #ffe6e6; padding: 20px; border-radius: 8px; margin: 20px; }}
    </style>
</head>
<body>
    <h1>S&P 500 Monitor</h1>
    <div class="error">
        <h2>Error Loading Data</h2>
        <p>Unable to fetch market data at this time.</p>
        <p>Error: {str(e)}</p>
        <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
        
        with open('sp500_dashboard.html', 'w') as f:
            f.write(error_html)
        
        return False

if __name__ == "__main__":
    get_data_and_create_simple_dashboard()
