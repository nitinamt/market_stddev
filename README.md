Key Features:

Fetches real-time S&P 500 data using the yfinance library
Calculates 200-day moving average and standard deviation
Checks if current price is between 2-3 standard deviations from the average
Market hours detection to avoid unnecessary runs when markets are closed
Comprehensive logging with timestamps and detailed analysis
JSON output for potential web dashboards
Alert system ready for notifications (email, Slack, etc.)

S&P 500 Standard Deviation Monitor 
What You Get

Interactive Plotly charts with zoom, hover, and pan functionality
Professional HTML dashboard with real-time metrics
Static PNG backup plots for reliability
Automated hourly updates during market hours
Free web hosting with Github

📊 Generated Files

sp500_dashboard.html - Main interactive dashboard
sp500_interactive.html - Standalone Plotly chart
sp500_analysis.png - Static backup chart
sp500_analysis.json - Raw data for APIs
sp500_monitor.log - Execution logs

Free Deployment
GitHub Pages 
Advantages: Free, reliable, automatic updates, version control
Setup:

Create a new GitHub repository
Upload all files (code + requirements.txt + workflow)
Go to Settings → Pages → Enable GitHub Pages
The workflow will automatically update your site hourly

Your dashboard will be at: https://yourusername.github.io/your-repo-name/sp500_dashboard.html
