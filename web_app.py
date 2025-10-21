#!/usr/bin/env python3
"""
Flask web application for Meraki Client Counter Dashboard.
Provides a responsive web interface for viewing client statistics and charts.
"""

from flask import Flask, render_template, jsonify, send_file, request
from datetime import datetime, timedelta
import logging
import os

from database import ClientDatabase
from data_processor import DataProcessor
from charts import ChartGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/stats/summary')
def get_summary_stats():
    """
    Get summary statistics (daily, weekly, monthly averages).

    Returns:
        JSON with current statistics
    """
    try:
        db = ClientDatabase()
        processor = DataProcessor()

        # Get all historical data
        clients = db.get_all_clients()

        if not clients:
            return jsonify({'error': 'No data available'}), 404

        # Calculate averages
        daily = processor.calculate_daily_averages(clients, days=7)
        weekly = processor.calculate_weekly_averages(clients, weeks=4)
        monthly = processor.calculate_monthly_averages(clients, months=3)

        # MAC randomization analysis
        mac_analysis = processor.analyze_mac_randomization(clients)

        # Database stats
        stats = db.get_stats()

        db.close()

        return jsonify({
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly,
            'mac_analysis': mac_analysis,
            'database': {
                'total_records': stats['total_records'],
                'unique_macs': stats['unique_mac_addresses'],
                'earliest_date': stats['earliest_date'],
                'latest_date': stats['latest_date']
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    except Exception as e:
        logger.error(f"Error getting summary stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/peak-hours')
def get_peak_hours():
    """
    Get peak hours analysis.

    Query parameters:
        days: Number of days to analyze (default: 7)

    Returns:
        JSON with peak hours data
    """
    try:
        days = int(request.args.get('days', 7))

        db = ClientDatabase()
        processor = DataProcessor()

        # Get recent data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        clients = db.get_clients_in_date_range(start_date, end_date)

        if not clients:
            return jsonify({'error': 'No data available for the specified period'}), 404

        # Analyze peak hours
        peak_analysis = processor.analyze_peak_hours(clients, days=days)

        db.close()

        return jsonify({
            'peak_analysis': peak_analysis,
            'period': {
                'start': start_date.isoformat() + 'Z',
                'end': end_date.isoformat() + 'Z',
                'days': days
            }
        })

    except Exception as e:
        logger.error(f"Error getting peak hours: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/hourly')
def get_hourly_stats():
    """
    Get hourly statistics for a specific date.

    Query parameters:
        date: Date to analyze (YYYY-MM-DD format, default: today)

    Returns:
        JSON with hourly statistics
    """
    try:
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        target_date = datetime.strptime(date_str, '%Y-%m-%d')

        db = ClientDatabase()
        processor = DataProcessor()

        # Get data for the specific day
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        clients = db.get_clients_in_date_range(start_date, end_date)

        if not clients:
            return jsonify({'error': f'No data available for {date_str}'}), 404

        # Calculate hourly stats
        hourly_stats = processor.calculate_hourly_stats(clients, days=1)

        db.close()

        return jsonify({
            'date': date_str,
            'hourly_stats': hourly_stats,
            'total_hours': len(hourly_stats)
        })

    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        logger.error(f"Error getting hourly stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/weekly')
def get_weekly_details():
    """
    Get detailed weekly statistics.

    Query parameters:
        weeks: Number of weeks to include (default: 52)

    Returns:
        JSON with weekly details
    """
    try:
        weeks = int(request.args.get('weeks', 52))

        db = ClientDatabase()
        processor = DataProcessor()

        clients = db.get_all_clients()

        if not clients:
            return jsonify({'error': 'No data available'}), 404

        weekly_data = processor.calculate_weekly_averages(clients, weeks=weeks)

        db.close()

        return jsonify({
            'weekly_data': weekly_data,
            'weeks_requested': weeks
        })

    except Exception as e:
        logger.error(f"Error getting weekly details: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/monthly')
def get_monthly_details():
    """
    Get detailed monthly statistics.

    Query parameters:
        months: Number of months to include (default: 12)

    Returns:
        JSON with monthly details
    """
    try:
        months = int(request.args.get('months', 12))

        db = ClientDatabase()
        processor = DataProcessor()

        clients = db.get_all_clients()

        if not clients:
            return jsonify({'error': 'No data available'}), 404

        monthly_data = processor.calculate_monthly_averages(clients, months=months)

        db.close()

        return jsonify({
            'monthly_data': monthly_data,
            'months_requested': months
        })

    except Exception as e:
        logger.error(f"Error getting monthly details: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<format>')
def export_data(format):
    """
    Export data in various formats.

    Args:
        format: Export format (json, csv)

    Returns:
        Downloadable file
    """
    try:
        from output import OutputFormatter

        db = ClientDatabase()
        processor = DataProcessor()
        formatter = OutputFormatter()

        clients = db.get_all_clients()

        if not clients:
            return jsonify({'error': 'No data available'}), 404

        # Calculate all statistics
        results = {
            'organization_name': 'Rochester Makerspace, Inc.',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'averages': {
                'daily': processor.calculate_daily_averages(clients, days=7),
                'weekly': processor.calculate_weekly_averages(clients, weeks=4),
                'monthly': processor.calculate_monthly_averages(clients, months=3)
            },
            'mac_randomization_analysis': processor.analyze_mac_randomization(clients)
        }

        db.close()

        if format == 'json':
            import json
            filename = f'meraki_stats_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
            filepath = f'/tmp/{filename}'
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            return send_file(filepath, as_attachment=True, download_name=filename)

        elif format == 'csv':
            filename = f'meraki_stats_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            filepath = f'/tmp/{filename}'
            formatter.save_csv(results, filepath)
            return send_file(filepath, as_attachment=True, download_name=filename)

        else:
            return jsonify({'error': 'Invalid format. Use json or csv'}), 400

    except Exception as e:
        logger.error(f"Error exporting data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Run the development server
    # In production, use a proper WSGI server like gunicorn
    app.run(host='0.0.0.0', port=5000, debug=True)
