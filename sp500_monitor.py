import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import logging
import os
import json

# Set matplotlib backend before importing pyplot
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sp500_monitor.log'),
        logging.StreamHandler()
    ]
)

def is_market_open():
    """Check if the US stock market is currently open"""
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    
    # Market is closed on weekends
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now <= market_close

def get_sp500_data():
    """Fetch S&P 500 data for analysis"""
    try:
        # Fetch more data to ensure we have enough for 200-day calculation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)  # Get extra days for holidays/weekends
        
        sp500 = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
        
        if sp500.empty:
            raise ValueError("No data retrieved from Yahoo Finance")
        
        return sp500
    except Exception as e:
        logging.error(f"Error fetching S&P 500 data: {e}")
        return None

def calculate_metrics(data):
    """Calculate 200-day moving average and standard deviation"""
    try:
        # Use closing prices
        closes = data['Close'].dropna()
        
        if len(closes) < 200:
            raise ValueError(f"Insufficient data: only {len(closes)} days available, need 200")
        
        # Calculate 200-day moving average
        ma_200 = closes.rolling(window=200).mean()
        
        # Calculate 200-day standard deviation
        std_200 = closes.rolling(window=200).std()
        
        # Get current price (latest close) - ensure scalar values
        current_price = float(closes.iloc[-1])
        current_ma = float(ma_200.iloc[-1])
        current_std = float(std_200.iloc[-1])
        
        # Calculate how many standard deviations away from the mean
        std_away = (current_price - current_ma) / current_std
        
        return {
            'current_price': current_price,
            'ma_200': current_ma,
            'std_200': current_std,
            'std_away': std_away,
            'date': closes.index[-1].strftime('%Y-%m-%d')
        }
    except Exception as e:
        logging.error(f"Error calculating metrics: {e}")
        return None

def check_deviation_range(metrics):
    """Check if the current price is between 2 and 3 standard deviations"""
    std_away = abs(metrics['std_away'])  # Use absolute value for both directions
    
    is_in_range = 2.0 <= std_away <= 3.0
    direction = "above" if metrics['std_away'] > 0 else "below"
    
    return {
        'in_range': is_in_range,
        'std_away': metrics['std_away'],
        'abs_std_away': std_away,
        'direction': direction
    }

def log_results(metrics, deviation_check):
    """Log the analysis results"""
    logging.info("="*50)
    logging.info("S&P 500 Standard Deviation Analysis")
    logging.info("="*50)
    logging.info(f"Date: {metrics['date']}")
    logging.info(f"Current S&P 500 Price: ${metrics['current_price']:.2f}")
    logging.info(f"200-Day Moving Average: ${metrics['ma_200']:.2f}")
    logging.info(f"200-Day Standard Deviation: ${metrics['std_200']:.2f}")
    logging.info(f"Standard Deviations from Mean: {metrics['std_away']:.2f}")
    logging.info(f"Direction: {deviation_check['direction']} average")
    
    if deviation_check['in_range']:
        logging.warning("🚨 ALERT: S&P 500 is between 2-3 standard deviations from 200-day average!")
        logging.warning(f"This indicates unusual market conditions ({deviation_check['abs_std_away']:.2f} std dev)")
    else:
        if deviation_check['abs_std_away'] < 2.0:
            logging.info("✅ Normal: S&P 500 is within 2 standard deviations")
        else:
            logging.warning(f"⚠️  Extreme: S&P 500 is beyond 3 standard deviations ({deviation_check['abs_std_away']:.2f})")
    
    logging.info("="*50)

def save_to_json(metrics, deviation_check):
    """Save results to JSON file for potential web dashboard"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'market_data': metrics,
        'analysis': deviation_check,
        'alert': deviation_check['in_range']
    }
    
    try:
        with open('sp500_analysis.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logging.info("Results saved to sp500_analysis.json")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")

def create_interactive_plot(data, metrics):
    """Create interactive Plotly chart"""
    try:
        # Calculate rolling statistics for the entire dataset
        closes = data['Close'].dropna()
        
        if len(closes) < 200:
            logging.error(f"Insufficient data for plotting: {len(closes)} days")
            return None
            
        ma_200 = closes.rolling(window=200).mean()
        std_200 = closes.rolling(window=200).std()
        
        # Calculate Bollinger Bands (2 and 3 standard deviations)
        upper_2std = ma_200 + (2 * std_200)
        lower_2std = ma_200 - (2 * std_200)
        upper_3std = ma_200 + (3 * std_200)
        lower_3std = ma_200 - (3 * std_200)
        
        # Get last 60 days for cleaner visualization (ensure we have enough data)
        last_60_days = min(-60, -len(closes) + 200)  # Don't go before we have MA data
        
        # Skip NaN values for plotting
        valid_indices = ~ma_200.isna()
        plot_data = closes[valid_indices]
        plot_dates = closes.index[valid_indices]
        
        if len(plot_data) < 60:
            plot_start = 0
        else:
            plot_start = len(plot_data) - 60
            
        dates = plot_dates[plot_start:]
        prices = plot_data.iloc[plot_start:]
        ma_200_plot = ma_200[valid_indices].iloc[plot_start:]
        upper_2std_plot = upper_2std[valid_indices].iloc[plot_start:]
        lower_2std_plot = lower_2std[valid_indices].iloc[plot_start:]
        upper_3std_plot = upper_3std[valid_indices].iloc[plot_start:]
        lower_3std_plot = lower_3std[valid_indices].iloc[plot_start:]
        
        # Create subplot
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('S&P 500 Price with Standard Deviation Bands', 'Standard Deviations from 200-Day MA'),
            vertical_spacing=0.12,
            row_heights=[0.7, 0.3]
        )
        
        # Main price chart
        fig.add_trace(
            go.Scatter(x=dates, y=prices, name='S&P 500', line=dict(color='black', width=2)),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=ma_200_plot, name='200-Day MA', line=dict(color='blue', width=2)),
            row=1, col=1
        )
        
        # Bollinger Bands
        fig.add_trace(
            go.Scatter(x=dates, y=upper_3std_plot, name='+3σ', line=dict(color='red', width=1, dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=upper_2std_plot, name='+2σ', line=dict(color='orange', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=lower_2std_plot, name='-2σ', line=dict(color='orange', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=dates, y=lower_3std_plot, name='-3σ', line=dict(color='red', width=1, dash='dash')),
            row=1, col=1
        )
        
        # Fill areas for 2-3σ zones
        fig.add_trace(
            go.Scatter(
                x=dates.tolist() + dates.tolist()[::-1],
                y=upper_2std_plot.tolist() + upper_3std_plot.tolist()[::-1],
                fill='toself',
                fillcolor='rgba(255, 0, 0, 0.1)',
                line=dict(color='rgba(255,255,255,0)'),
                name='Alert Zone (+2σ to +3σ)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates.tolist() + dates.tolist()[::-1],
                y=lower_3std_plot.tolist() + lower_2std_plot.tolist()[::-1],
                fill='toself',
                fillcolor='rgba(255, 0, 0, 0.1)',
                line=dict(color='rgba(255,255,255,0)'),
                name='Alert Zone (-3σ to -2σ)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Standard deviation subplot
        std_away_series = (closes - ma_200) / std_200
        std_away_plot = std_away_series[valid_indices].iloc[plot_start:]
        
        # Color points based on alert zone
        colors = []
        for x in std_away_plot:
            if pd.isna(x):
                colors.append('gray')
            elif abs(x) >= 2 and abs(x) <= 3:
                colors.append('red')
            elif abs(x) < 2:
                colors.append('green')
            else:
                colors.append('darkred')
        
        fig.add_trace(
            go.Scatter(
                x=dates, 
                y=std_away_plot, 
                mode='markers+lines',
                name='Standard Deviations',
                line=dict(color='gray', width=1),
                marker=dict(color=colors, size=6)
            ),
            row=2, col=1
        )
        
        # Add horizontal lines for reference
        fig.add_hline(y=2, line_dash="dash", line_color="orange", row=2, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="orange", row=2, col=1)
        fig.add_hline(y=3, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=-3, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="blue", row=2, col=1)
        
        # Highlight current point
        current_date = dates.iloc[-1] if len(dates) > 0 else closes.index[-1]
        current_price = prices.iloc[-1] if len(prices) > 0 else closes.iloc[-1]
        current_std_away = std_away_plot.iloc[-1] if len(std_away_plot) > 0 else metrics['std_away']
        
        fig.add_trace(
            go.Scatter(
                x=[current_date], 
                y=[current_price], 
                mode='markers',
                marker=dict(color='red' if abs(current_std_away) >= 2 and abs(current_std_away) <= 3 else 'blue', 
                           size=12, symbol='star'),
                name='Current Price',
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[current_date], 
                y=[current_std_away], 
                mode='markers',
                marker=dict(color='red' if abs(current_std_away) >= 2 and abs(current_std_away) <= 3 else 'blue', 
                           size=12, symbol='star'),
                name='Current σ',
                showlegend=True
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f'S&P 500 Standard Deviation Analysis - {metrics["date"]}<br>'
                       f'Current: ${metrics["current_price"]:.2f} | '
                       f'200-day MA: ${metrics["ma_200"]:.2f} | '
                       f'σ from MA: {metrics["std_away"]:.2f}',
                'x': 0.5,
                'xanchor': 'center'
            },
            height=800,
            showlegend=True,
            hovermode='x unified'
        )
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Standard Deviations", row=2, col=1)
        
        return fig
        
    except Exception as e:
        logging.error(f"Error creating interactive plot: {e}")
        return None

def create_static_plot(data, metrics):
    """Create static matplotlib chart as backup"""
    try:
        plt.style.use('default')  # Changed from 'seaborn-v0_8' which may not be available
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Calculate rolling statistics
        closes = data['Close'].dropna()
        ma_200 = closes.rolling(window=200).mean()
        std_200 = closes.rolling(window=200).std()
        
        # Calculate Bollinger Bands
        upper_2std = ma_200 + (2 * std_200)
        lower_2std = ma_200 - (2 * std_200)
        upper_3std = ma_200 + (3 * std_200)
        lower_3std = ma_200 - (3 * std_200)
        
        # Plot last 60 days
        last_60_days = -60
        dates = closes.index[last_60_days:]
        
        # Main price chart
        ax1.plot(dates, closes.iloc[last_60_days:], 'k-', linewidth=2, label='S&P 500')
        ax1.plot(dates, ma_200.iloc[last_60_days:], 'b-', linewidth=2, label='200-Day MA')
        ax1.plot(dates, upper_2std.iloc[last_60_days:], 'orange', linewidth=1, label='±2σ')
        ax1.plot(dates, lower_2std.iloc[last_60_days:], 'orange', linewidth=1)
        ax1.plot(dates, upper_3std.iloc[last_60_days:], 'r--', linewidth=1, label='±3σ')
        ax1.plot(dates, lower_3std.iloc[last_60_days:], 'r--', linewidth=1)
        
        # Fill alert zones
        ax1.fill_between(dates, upper_2std.iloc[last_60_days:], upper_3std.iloc[last_60_days:], 
                        alpha=0.2, color='red', label='Alert Zone')
        ax1.fill_between(dates, lower_2std.iloc[last_60_days:], lower_3std.iloc[last_60_days:], 
                        alpha=0.2, color='red')
        
        # Current point
        current_price = closes.iloc[-1]
        current_date = dates[-1]
        ax1.plot(current_date, current_price, 'ro', markersize=10, label='Current')
        
        ax1.set_title(f'S&P 500 - {metrics["date"]} | Current: ${current_price:.2f} | σ: {metrics["std_away"]:.2f}')
        ax1.set_ylabel('Price ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Standard deviation chart
        std_away_series = (closes - ma_200) / std_200
        ax2.plot(dates, std_away_series.iloc[last_60_days:], 'gray', linewidth=1)
        ax2.scatter(dates, std_away_series.iloc[last_60_days:], 
                   c=['red' if abs(x) >= 2 and abs(x) <= 3 else 'green' if abs(x) < 2 else 'darkred' 
                      for x in std_away_series.iloc[last_60_days:]], s=20)
        
        ax2.axhline(y=2, color='orange', linestyle='--', alpha=0.7)
        ax2.axhline(y=-2, color='orange', linestyle='--', alpha=0.7)
        ax2.axhline(y=3, color='red', linestyle='--', alpha=0.7)
        ax2.axhline(y=-3, color='red', linestyle='--', alpha=0.7)
        ax2.axhline(y=0, color='blue', linestyle='-', alpha=0.7)
        
        # Current point
        ax2.plot(current_date, metrics['std_away'], 'ro', markersize=10)
        
        ax2.set_title('Standard Deviations from 200-Day Moving Average')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Standard Deviations')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
        
    except Exception as e:
        logging.error(f"Error creating static plot: {e}")
        return None

def create_html_dashboard(metrics, deviation_check, interactive_plot=None):
    """Create HTML dashboard with embedded plot"""
    try:
        # Convert plot to HTML if available
        if interactive_plot:
            plot_html = pyo.plot(interactive_plot, output_type='div', include_plotlyjs=True, config={'displayModeBar': True})
        else:
            # Fallback: show static image or placeholder
            plot_html = """
            <div style="text-align: center; padding: 50px; background: #f8f9fa; border-radius: 8px;">
                <h3>Chart Generation Error</h3>
                <p>Unable to generate interactive chart. Check logs for details.</p>
                <p>Static chart may be available as sp500_analysis.png</p>
            </div>
            """
        
        # Determine status and styling
        if deviation_check['in_range']:
            status = "🚨 ALERT"
            status_class = "alert"
            status_color = "#ff4444"
        elif deviation_check['abs_std_away'] < 2.0:
            status = "✅ NORMAL"
            status_class = "normal"
            status_color = "#44ff44"
        else:
            status = "⚠️ EXTREME"
            status_class = "extreme"
            status_color = "#ff8800"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S&P 500 Standard Deviation Monitor</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .status {{
            font-size: 1.5em;
            font-weight: bold;
            margin: 10px 0;
            color: {status_color};
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        .chart-container {{
            padding: 20px;
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        .explanation {{
            padding: 30px;
            line-height: 1.6;
            color: #555;
        }}
        .explanation h3 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        @media (max-width: 768px) {{
            .metrics {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 2em;
            }}
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
                <div class="metric-value">${metrics['current_price']:.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">200-Day Average</div>
                <div class="metric-value">${metrics['ma_200']:.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Standard Deviations</div>
                <div class="metric-value" style="color: {status_color};">{metrics['std_away']:.2f}σ</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Direction</div>
                <div class="metric-value">{deviation_check['direction'].title()}</div>
            </div>
        </div>
        
        <div class="chart-container">
            {plot_html}
        </div>
        
        <div class="explanation">
            <h3>Understanding the Analysis</h3>
            <p><strong>Standard Deviation Bands:</strong> These show how far the current price is from the 200-day moving average in terms of standard deviations.</p>
            
            <p><strong>Alert Zone (2-3σ):</strong> When the S&P 500 is between 2 and 3 standard deviations from its 200-day average, it indicates unusual market conditions that may warrant attention.</p>
            
            <p><strong>Interpretation:</strong></p>
            <ul>
                <li><span style="color: #44ff44;"><strong>Normal (< 2σ):</strong></span> Price is within typical range</li>
                <li><span style="color: #ff4444;"><strong>Alert (2-3σ):</strong></span> Unusual conditions - potential opportunity or risk</li>
                <li><span style="color: #ff8800;"><strong>Extreme (> 3σ):</strong></span> Very rare conditions - significant market event</li>
            </ul>
            
            <p><strong>Current Status:</strong> The S&P 500 is currently <strong>{deviation_check['abs_std_away']:.2f} standard deviations {deviation_check['direction']}</strong> its 200-day moving average.</p>
        </div>
        
        <div class="footer">
            <p>Data source: Yahoo Finance | Analysis updated hourly during market hours</p>
            <p>This is for informational purposes only and should not be considered investment advice.</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open('sp500_dashboard.html', 'w') as f:
            f.write(html_content)
        
        logging.info("HTML dashboard created: sp500_dashboard.html")
        return True
        
    except Exception as e:
        logging.error(f"Error creating HTML dashboard: {e}")
        return False

def send_notification(metrics, deviation_check):
    """Send notification if in alert range (placeholder for email/webhook)"""
    if deviation_check['in_range']:
        # Placeholder for notification system
        # You can integrate with email services, Slack webhooks, etc.
        alert_message = (
            f"🚨 S&P 500 ALERT 🚨\n"
            f"Price: ${metrics['current_price']:.2f}\n"
            f"200-day MA: ${metrics['ma_200']:.2f}\n"
            f"Standard Deviations: {metrics['std_away']:.2f}\n"
            f"Direction: {deviation_check['direction']} average\n"
            f"Date: {metrics['date']}"
        )
        
        logging.info("NOTIFICATION TRIGGERED:")
        logging.info(alert_message)
        
        # Example webhook notification (uncomment and configure as needed)
        # import requests
        # webhook_url = os.getenv('WEBHOOK_URL')
        # if webhook_url:
        #     requests.post(webhook_url, json={'text': alert_message})

def main():
    """Main execution function"""
    logging.info("Starting S&P 500 standard deviation check...")
    
    # Check if market is open (optional - remove if you want to run regardless)
    if not is_market_open():
        logging.info("Market is currently closed. Running analysis anyway...")
        # Changed to continue running even when market is closed
    
    # Fetch data
    data = get_sp500_data()
    if data is None:
        logging.error("Failed to fetch data. Exiting.")
        return
    
    # Calculate metrics
    metrics = calculate_metrics(data)
    if metrics is None:
        logging.error("Failed to calculate metrics. Exiting.")
        return
    
    # Check deviation range
    deviation_check = check_deviation_range(metrics)
    
    # Log results
    log_results(metrics, deviation_check)
    
    # Create plots
    logging.info("Creating interactive plot...")
    interactive_plot = create_interactive_plot(data, metrics)
    
    # Always create HTML dashboard (even if plot fails)
    logging.info("Creating HTML dashboard...")
    dashboard_created = create_html_dashboard(metrics, deviation_check, interactive_plot)
    
    if interactive_plot:
        # Save interactive plot
        try:
            pyo.plot(interactive_plot, filename='sp500_interactive.html', auto_open=False)
            logging.info("Interactive plot saved: sp500_interactive.html")
        except Exception as e:
            logging.error(f"Error saving interactive plot: {e}")
    else:
        logging.warning("Interactive plot creation failed")
    
    # Create static plot as backup
    logging.info("Creating static plot...")
    static_plot = create_static_plot(data, metrics)
    if static_plot:
        try:
            static_plot.savefig('sp500_analysis.png', dpi=300, bbox_inches='tight')
            plt.close(static_plot)
            logging.info("Static plot saved: sp500_analysis.png")
        except Exception as e:
            logging.error(f"Error saving static plot: {e}")
            plt.close('all')  # Clean up any remaining plots
    
    # Save to JSON
    save_to_json(metrics, deviation_check)
    
    # Send notification if needed
    send_notification(metrics, deviation_check)
    
    logging.info("Analysis complete with visualizations.")

if __name__ == "__main__":
    main()