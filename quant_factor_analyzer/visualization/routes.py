import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import numpy as np
from flask import current_app, url_for, render_template, Blueprint, flash # Added flash

from werkzeug.utils import secure_filename

vis_bp = Blueprint('visualization', __name__, 
                   template_folder='templates') # Removed blueprint static folder config, will use app's static folder

@vis_bp.route('/ic_timeseries_chart/<factor_filename>')
def ic_timeseries_chart_route(factor_filename):
    s_factor_filename = secure_filename(factor_filename) # Secure the filename

    # Generate Plot
    x = np.arange(0, 10, 0.1)
    y = np.sin(x)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.set_title(f'Placeholder IC Time Series for {s_factor_filename}')
    ax.set_xlabel('Time')
    ax.set_ylabel('IC Value')

    # Save Plot to File (in project_root/static/charts_generated)
    # current_app.static_folder refers to the app's static folder (project_root/static)
    charts_dir = os.path.join(current_app.static_folder, 'charts_generated')
    os.makedirs(charts_dir, exist_ok=True)
    
    # Use a simplified and secure name for the chart file
    chart_filename = f'ic_timeseries_{s_factor_filename}.png'
    chart_filepath = os.path.join(charts_dir, chart_filename)
    
    try:
        fig.savefig(chart_filepath)
    except Exception as e:
        plt.close(fig)
        current_app.logger.error(f"Error saving chart: {e}")
        flash("Error generating chart image.", "error")
        # Potentially redirect to a general error page or back
        return redirect(url_for('data_management.upload_data_route')) 
    finally:
        plt.close(fig)

    # Render Template
    # url_for('static', ...) correctly points to the app's root static folder
    chart_url = url_for('static', filename=f'charts_generated/{chart_filename}')
    
    return render_template('visualization/ic_timeseries_chart.html', 
                           chart_url=chart_url, 
                           factor_filename=s_factor_filename)

@vis_bp.route('/cumulative_return_chart/<factor_filename>')
def cumulative_return_chart_route(factor_filename):
    s_factor_filename = secure_filename(factor_filename)

    # Generate Plot
    data = np.random.randn(100).cumsum() # Random walk for placeholder
    fig, ax = plt.subplots()
    ax.plot(data)
    ax.set_title(f'Placeholder Cumulative Return Curve for {s_factor_filename}')
    ax.set_xlabel('Time')
    ax.set_ylabel('Cumulative Return')

    # Save Plot to File
    charts_dir = os.path.join(current_app.static_folder, 'charts_generated')
    os.makedirs(charts_dir, exist_ok=True) # Good practice, though likely exists
    
    chart_filename = f'cumulative_return_{s_factor_filename}.png'
    chart_filepath = os.path.join(charts_dir, chart_filename)
    
    try:
        fig.savefig(chart_filepath)
    except Exception as e:
        plt.close(fig)
        current_app.logger.error(f"Error saving cumulative return chart: {e}")
        flash(f"Error generating cumulative return chart image for {s_factor_filename}.", "error")
        return redirect(url_for('data_management.upload_data_route')) # Or back to preview
    finally:
        plt.close(fig)

    # Render Template
    chart_url = url_for('static', filename=f'charts_generated/{chart_filename}')
    
    return render_template('visualization/cumulative_return_chart.html', 
                           chart_url=chart_url, 
                           factor_filename=s_factor_filename)
