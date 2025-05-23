from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from werkzeug.utils import secure_filename
import os
import pandas as pd
import numpy as np # Ensure numpy is imported
import io
# os is already imported by Flask/werkzeug or implicitly available, but good to ensure it's accessible for os.listdir, os.path.exists

data_bp = Blueprint('data_management', __name__, template_folder='templates')

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@data_bp.route('/upload', methods=['GET', 'POST'])
def upload_data_route():
    if request.method == 'POST':
        factor_file = request.files.get('factor_file')
        price_file = request.files.get('price_file')

        # Using paths from app.config, relative to instance_path
        # UPLOAD_FOLDER_DATA and UPLOAD_FOLDER_PRICES are like 'uploads/data'
        upload_path_data_abs = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_DATA'])
        upload_path_prices_abs = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_PRICES'])

        # Directories are already created in __init__.py, but good practice for blueprints that might be used elsewhere
        os.makedirs(upload_path_data_abs, exist_ok=True)
        os.makedirs(upload_path_prices_abs, exist_ok=True)

        if factor_file and factor_file.filename != '':
            if allowed_file(factor_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                factor_filename = secure_filename(factor_file.filename)
                factor_filepath = os.path.join(upload_path_data_abs, factor_filename)
                factor_file.save(factor_filepath)

                try:
                    if factor_filename.endswith('.csv'):
                        df = pd.read_csv(factor_filepath, index_col=[0,1])
                    else: # .xls or .xlsx
                        df = pd.read_excel(factor_filepath, index_col=[0,1])

                    if not isinstance(df.index, pd.MultiIndex):
                        os.remove(factor_filepath)
                        flash(f"Validation Error for '{factor_filename}': Index is not a MultiIndex. File removed.", 'error')
                    elif [name.lower().strip() for name in df.index.names] != ['day', 'sec']:
                        os.remove(factor_filepath)
                        flash(f"Validation Error for '{factor_filename}': Index levels must be 'day' and 'sec' (in that order). File removed.", 'error')
                    else:
                        try:
                            # Attempt to parse 'day' level as datetime to check format
                            pd.to_datetime(df.index.get_level_values('day'))
                            flash(f"Factor file '{factor_filename}' uploaded and validated successfully. Redirecting to preview.", 'success')
                            return redirect(url_for('data_management.preview_factor_data_route', filename=factor_filename)) # Redirect to preview
                        except Exception as e_date:
                            os.remove(factor_filepath)
                            flash(f"Validation Error for '{factor_filename}': 'day' level cannot be parsed as dates. Error: {e_date}. File removed.", 'error')
                
                except Exception as e_read:
                    if os.path.exists(factor_filepath): # File might not exist if save failed, or read failed early
                        os.remove(factor_filepath)
                    flash(f"Error processing file '{factor_filename}': {e_read}. Ensure it's a valid CSV/Excel file with first two columns as index. File removed.", 'error')
            else:
                flash(f"Invalid file type for factor data '{factor_file.filename}'. Allowed types: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}.", 'error')
        elif factor_file and factor_file.filename == '': # If factor_file input is present but no file selected
            pass # Don't flash error if only price file is uploaded or no file selected
        
        if price_file and price_file.filename != '':
            if allowed_file(price_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                price_filename = secure_filename(price_file.filename)
                price_filepath = os.path.join(upload_path_prices_abs, price_filename)
                price_file.save(price_filepath)

                EXPECTED_PRICE_COLS = ['open', 'high', 'low', 'close']

                try:
                    if price_filename.endswith('.csv'):
                        df_price = pd.read_csv(price_filepath, index_col=[0,1])
                    else: # .xls or .xlsx
                        df_price = pd.read_excel(price_filepath, index_col=[0,1])

                    # MultiIndex Check
                    if not isinstance(df_price.index, pd.MultiIndex):
                        os.remove(price_filepath)
                        flash(f"Validation Error for price file '{price_filename}': Index is not a MultiIndex. File removed.", 'error')
                    elif [name.lower().strip() for name in df_price.index.names] != ['day', 'sec']:
                        os.remove(price_filepath)
                        flash(f"Validation Error for price file '{price_filename}': Index levels must be 'day' and 'sec'. File removed.", 'error')
                    else:
                        # 'day' Level Datetime Check
                        try:
                            pd.to_datetime(df_price.index.get_level_values('day'))
                            
                            # Column Check (case-insensitive)
                            df_price_cols_lower = [col.lower().strip() for col in df_price.columns]
                            expected_cols_lower = [col.lower() for col in EXPECTED_PRICE_COLS]
                            
                            if not all(expected_col in df_price_cols_lower for expected_col in expected_cols_lower):
                                os.remove(price_filepath)
                                missing_cols = [col for col in expected_cols_lower if col not in df_price_cols_lower]
                                flash(f"Validation Error for price file '{price_filename}': Missing expected columns: {', '.join(missing_cols)}. File removed.", 'error')
                            else:
                                flash(f"Price file '{price_filename}' uploaded and validated successfully.", 'success')

                        except Exception as e_date:
                            os.remove(price_filepath)
                            flash(f"Validation Error for price file '{price_filename}': 'day' level cannot be parsed as dates. Error: {e_date}. File removed.", 'error')
                
                except Exception as e_read_price:
                    if os.path.exists(price_filepath):
                        os.remove(price_filepath)
                    flash(f"Error processing price file '{price_filename}': {e_read_price}. Ensure it's a valid CSV/Excel file with first two columns as index. File removed.", 'error')
            else:
                flash(f"Invalid file type for price data '{price_file.filename}'. Allowed types: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}.", 'error')
        elif price_file and price_file.filename == '': # If price_file input is present but no file selected
            pass # Don't flash error if only factor file is uploaded or no file selected
        
        # If execution reaches this point, it means either:
        # 1. No factor file was uploaded or it was invalid (an error message would be flashed, and file removed if needed).
        # 2. Only a price file was uploaded (message flashed).
        # 3. No files were uploaded.
        # In all these cases, redirect back to the upload page.
        # A successful factor file upload would have already returned a redirect to the preview page.
        return redirect(url_for('data_management.upload_data_route'))

    return render_template('data_management/upload_data.html') # This is for GET requests

@data_bp.route('/preview/factor/<filename>')
def preview_factor_data_route(filename):
    s_filename = secure_filename(filename) # Secure the input filename
    factor_filepath = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_DATA'], s_filename)

    if not os.path.exists(factor_filepath):
        flash(f"Error: Factor file '{s_filename}' not found. It might have been deleted or moved.", 'error')
        return redirect(url_for('data_management.upload_data_route'))

    # Scan for available price files
    available_price_files = []
    price_upload_path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_PRICES'])
    if os.path.exists(price_upload_path):
        for f_name in os.listdir(price_upload_path):
            # A more robust check would be to see if these files previously passed validation
            # For now, just list them if they have the correct extension
            if f_name.endswith(('.csv', '.xlsx', '.xls')):
                available_price_files.append(f_name)
    
    aligned_with_price_file_param = request.args.get('aligned_with_price_file')

    try:
        # Load factor DataFrame
        if s_filename.endswith('.csv'):
            df_factor = pd.read_csv(factor_filepath, index_col=[0,1])
        else: # .xls or .xlsx
            df_factor = pd.read_excel(factor_filepath, index_col=[0,1])

        # Perform initial validation on factor_df
        if not isinstance(df_factor.index, pd.MultiIndex) or [name.lower().strip() for name in df_factor.index.names] != ['day', 'sec']:
             flash(f"Error: Factor file '{s_filename}' is not in the expected format (MultiIndex with 'day', 'sec'). Please re-upload.", 'error')
             return redirect(url_for('data_management.upload_data_route'))
        try:
            pd.to_datetime(df_factor.index.get_level_values('day')) # Check 'day' level
        except Exception as e_date_factor:
            flash(f"Error in factor file '{s_filename}': 'day' level cannot be parsed as dates. Error: {e_date_factor}. Please re-upload.", 'error')
            return redirect(url_for('data_management.upload_data_route'))


        if aligned_with_price_file_param:
            s_aligned_price_filename = secure_filename(aligned_with_price_file_param)
            price_filepath_to_align = os.path.join(price_upload_path, s_aligned_price_filename)

            if not os.path.exists(price_filepath_to_align):
                flash(f"Error: Selected price file '{s_aligned_price_filename}' for alignment not found.", 'error')
            else:
                try:
                    if s_aligned_price_filename.endswith('.csv'):
                        df_price = pd.read_csv(price_filepath_to_align, index_col=[0,1])
                    else:
                        df_price = pd.read_excel(price_filepath_to_align, index_col=[0,1])
                    
                    # Validate price_df index before intersection
                    if not isinstance(df_price.index, pd.MultiIndex) or [name.lower().strip() for name in df_price.index.names] != ['day', 'sec']:
                        flash(f"Error: Price file '{s_aligned_price_filename}' is not in the expected format for alignment (MultiIndex with 'day', 'sec').", 'error')
                    else:
                        try:
                            pd.to_datetime(df_price.index.get_level_values('day')) # Check 'day' level for price data
                            
                            common_index = df_factor.index.intersection(df_price.index)
                            if common_index.empty:
                                 flash(f"No common time series data (day, sec) found between '{s_filename}' and '{s_aligned_price_filename}'. Displaying original factor data.", 'warning')
                            else:
                                df_factor = df_factor.loc[common_index]
                                flash(f"Displaying factor data aligned with '{s_aligned_price_filename}'. Original factor file not modified.", 'info')
                        except Exception as e_date_price:
                             flash(f"Error in price file '{s_aligned_price_filename}': 'day' level cannot be parsed as dates. Error: {e_date_price}. Alignment not performed.", 'error')
                except Exception as e_price_read:
                    flash(f"Error reading or processing price file '{s_aligned_price_filename}' for alignment: {e_price_read}", 'error')

        # Proceed with df_factor (original or aligned) for previews
        head_html = df_factor.head().to_html(classes='table table-striped', border=1)
        describe_html = df_factor.describe().to_html(classes='table table-striped', border=1)
        
        buffer = io.StringIO()
        df_factor.info(buf=buffer)
        info_str = buffer.getvalue()

        missing_values_per_column = df_factor.isnull().sum()
        missing_values_html = missing_values_per_column.to_frame(name='Missing Count').to_html(classes='table table-striped', border=1)

        outlier_stats = []
        numeric_cols = df_factor.select_dtypes(include=np.number).columns
        if not numeric_cols.empty:
            for col in numeric_cols:
                mean = df_factor[col].mean()
                std = df_factor[col].std()
                lower_bound_sigma = mean - 3 * std
                upper_bound_sigma = mean + 3 * std
                outliers_3sigma_count = df_factor[col][(df_factor[col] < lower_bound_sigma) | (df_factor[col] > upper_bound_sigma)].count()

                q1 = df_factor[col].quantile(0.25)
                q3 = df_factor[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound_iqr = q1 - 1.5 * iqr
                upper_bound_iqr = q3 + 1.5 * iqr
                outliers_iqr_count = df_factor[col][(df_factor[col] < lower_bound_iqr) | (df_factor[col] > upper_bound_iqr)].count()
                
                outlier_stats.append({
                    'column': col, 
                    'sigma_count': outliers_3sigma_count, 
                    'iqr_count': outliers_iqr_count
                })

        return render_template('data_management/preview_data.html', 
                               filename=s_filename, # Use secured filename
                               head_html=head_html, 
                               describe_html=describe_html, 
                               info_str=info_str,
                               missing_values_html=missing_values_html,
                               outlier_stats=outlier_stats,
                               available_price_files=available_price_files, # Pass available price files
                               aligned_with_price_file=aligned_with_price_file_param) # Pass the name of the aligned file for display

    except Exception as e:
        flash(f"Error processing factor file '{s_filename}' for preview: {e}. Please try re-uploading.", 'error')
        return redirect(url_for('data_management.upload_data_route'))

@data_bp.route('/preprocess/missing/<filename>', methods=['GET', 'POST'])
def handle_missing_values_route(filename):
    if request.method == 'POST':
        strategy = request.form.get('global_mv_strategy')
        
        if not strategy:
            flash("No missing value handling strategy was selected. Please choose a strategy.", "warning")
            return redirect(url_for('data_management.preview_factor_data_route', filename=filename))

        # Secure the filename again before using it to construct path
        s_filename = secure_filename(filename)
        filepath = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_DATA'], s_filename)

        if not os.path.exists(filepath):
            flash(f"Error: File '{s_filename}' not found. Cannot apply preprocessing.", 'error')
            return redirect(url_for('data_management.upload_data_route'))

        try:
            if s_filename.endswith('.csv'):
                df = pd.read_csv(filepath, index_col=[0,1])
            else: # .xls or .xlsx
                df = pd.read_excel(filepath, index_col=[0,1])
            
            original_missing_count = df.isnull().sum().sum()

            if strategy == 'ffill':
                df.fillna(method='ffill', inplace=True)
            elif strategy == 'bfill':
                df.fillna(method='bfill', inplace=True)
            elif strategy == 'interpolate_linear':
                # df.interpolate(method='linear', inplace=True) # This might affect non-numeric if not careful
                for col in df.select_dtypes(include=pd.np.number).columns: # Iterate only over numeric columns
                    df[col].interpolate(method='linear', inplace=True)
            elif strategy == 'delete_rows':
                df.dropna(inplace=True)
            elif strategy == 'fill_mean':
                for col in df.select_dtypes(include=pd.np.number).columns:
                    df[col].fillna(df[col].mean(), inplace=True)
            elif strategy == 'fill_median':
                for col in df.select_dtypes(include=pd.np.number).columns:
                    df[col].fillna(df[col].median(), inplace=True)
            else:
                flash(f"Invalid strategy '{strategy}' selected.", "error")
                return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))

            # Save the processed DataFrame
            if s_filename.endswith('.csv'):
                df.to_csv(filepath, index=True)
            else: # .xls or .xlsx
                df.to_excel(filepath, index=True)
            
            new_missing_count = df.isnull().sum().sum()
            flash(f"Missing values handled using '{strategy}' strategy for file '{s_filename}'. {original_missing_count - new_missing_count} values filled/removed.", 'success')

        except Exception as e:
            flash(f"Error processing file '{s_filename}' with strategy '{strategy}': {e}", 'error')
        
        return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))
    
    # GET request to this route (e.g. if user navigates directly)
    flash("Please select a missing value strategy using the form.", "info")
    return redirect(url_for('data_management.preview_factor_data_route', filename=filename))

@data_bp.route('/preprocess/outliers/<filename>', methods=['GET', 'POST'])
def handle_outliers_route(filename):
    if request.method == 'POST':
        strategy = request.form.get('global_outlier_strategy')
        
        if not strategy:
            flash("No outlier handling strategy was selected. Please choose a strategy.", "warning")
            return redirect(url_for('data_management.preview_factor_data_route', filename=filename))

        s_filename = secure_filename(filename)
        filepath = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_DATA'], s_filename)

        if not os.path.exists(filepath):
            flash(f"Error: File '{s_filename}' not found. Cannot apply outlier handling.", 'error')
            return redirect(url_for('data_management.upload_data_route'))

        try:
            if s_filename.endswith('.csv'):
                df = pd.read_csv(filepath, index_col=[0,1])
            else: # .xls or .xlsx
                df = pd.read_excel(filepath, index_col=[0,1])
            
            numeric_cols = df.select_dtypes(include=np.number).columns
            if numeric_cols.empty:
                flash(f"No numeric columns found in '{s_filename}' to apply outlier handling.", "info")
                return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))

            for col in numeric_cols:
                if strategy == 'cap_1_99':
                    lower_percentile = df[col].quantile(0.01)
                    upper_percentile = df[col].quantile(0.99)
                    df[col] = np.clip(df[col], lower_percentile, upper_percentile)
                elif strategy == 'clamp_3sigma':
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - 3 * std
                    upper_bound = mean + 3 * std
                    df[col] = np.clip(df[col], lower_bound, upper_bound)
                elif strategy == 'set_null_3sigma':
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - 3 * std
                    upper_bound = mean + 3 * std
                    df.loc[(df[col] < lower_bound) | (df[col] > upper_bound), col] = np.nan
                else:
                    # This case should ideally not be reached if the form is correctly submitted
                    flash(f"Invalid outlier strategy '{strategy}' selected.", "error")
                    return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))
            
            # Save the processed DataFrame
            if s_filename.endswith('.csv'):
                df.to_csv(filepath, index=True)
            else: # .xls or .xlsx
                df.to_excel(filepath, index=True)
            
            flash(f"Outliers handled using '{strategy}' strategy for file '{s_filename}'.", 'success')

        except Exception as e:
            flash(f"Error processing file '{s_filename}' with outlier strategy '{strategy}': {e}", 'error')
        
        return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))
    
    # GET request
    flash("Please select an outlier handling strategy using the form.", "info")
    return redirect(url_for('data_management.preview_factor_data_route', filename=filename))

from sklearn.preprocessing import StandardScaler, MinMaxScaler # Added

@data_bp.route('/preprocess/standardize/<filename>', methods=['GET', 'POST'])
def handle_standardization_route(filename):
    if request.method == 'POST':
        strategy = request.form.get('standardization_strategy')
        s_filename = secure_filename(filename) # Secure filename before use
        filepath = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER_DATA'], s_filename)

        if not strategy:
            flash("No standardization strategy was selected. Please choose a strategy.", "warning")
            return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))

        if not os.path.exists(filepath):
            flash(f"Error: File '{s_filename}' not found. Cannot apply standardization.", 'error')
            return redirect(url_for('data_management.upload_data_route'))

        if strategy == 'rankic':
            flash(f"RankIC transformation for {s_filename} is not yet implemented.", "info")
            return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))

        try:
            if s_filename.endswith('.csv'):
                df = pd.read_csv(filepath, index_col=[0,1])
            else: # .xls or .xlsx
                df = pd.read_excel(filepath, index_col=[0,1])
            
            numeric_cols = df.select_dtypes(include=np.number).columns
            if numeric_cols.empty:
                flash(f"No numeric columns found in '{s_filename}' to apply standardization.", "info")
                return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))

            for col_name in numeric_cols:
                # Reshape column for scaler: df[[col_name]]
                if strategy == 'zscore':
                    scaler = StandardScaler()
                    df[col_name] = scaler.fit_transform(df[[col_name]])
                elif strategy == 'minmax':
                    scaler = MinMaxScaler()
                    df[col_name] = scaler.fit_transform(df[[col_name]])
                else:
                    flash(f"Invalid or not yet implemented standardization strategy '{strategy}' selected.", "error")
                    return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))
            
            # Save the processed DataFrame
            if s_filename.endswith('.csv'):
                df.to_csv(filepath, index=True)
            else: # .xls or .xlsx
                df.to_excel(filepath, index=True)
            
            flash(f"Data standardized using '{strategy}' strategy for file '{s_filename}'.", 'success')

        except Exception as e:
            flash(f"Error applying standardization strategy '{strategy}' to file '{s_filename}': {e}", 'error')
        
        return redirect(url_for('data_management.preview_factor_data_route', filename=s_filename))
    
    # GET request
    flash("Please select a standardization strategy using the form.", "info")
    return redirect(url_for('data_management.preview_factor_data_route', filename=filename))
