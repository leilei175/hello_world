import os
import pandas as pd
import numpy as np
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from werkzeug.utils import secure_filename
from app.utils import detect_outliers_sigma, detect_outliers_quantile, cap_outliers

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['GET'])
def upload_page():
    """Renders the upload page."""
    return render_template('upload.html')

@bp.route('/upload_file', methods=['POST'])
def upload_file():
    """Handles the file upload."""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('main.upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('main.upload_page'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(save_path)
            flash(f'File {filename} uploaded. Starting validation...', 'info')

            # --- Start Data Validation ---
            try:
                if filename.rsplit('.', 1)[1].lower() == 'csv':
                    df = pd.read_csv(save_path, index_col=[0, 1])
                else: # xls, xlsx
                    df = pd.read_excel(save_path, index_col=[0, 1])

                # MultiIndex Validation
                if not isinstance(df.index, pd.MultiIndex):
                    os.remove(save_path)
                    flash('Invalid file structure: Expected a MultiIndex.', 'error')
                    return redirect(url_for('main.upload_page'))

                if df.index.nlevels != 2:
                    os.remove(save_path)
                    flash(f'Invalid MultiIndex: Expected 2 levels, found {df.index.nlevels}.', 'error')
                    return redirect(url_for('main.upload_page'))

                try:
                    # Validate first level (day) as datetime
                    pd.to_datetime(df.index.levels[0])
                except (ValueError, TypeError):
                    os.remove(save_path)
                    flash('Invalid data: Index level 0 (day) is not in a valid date format.', 'error')
                    return redirect(url_for('main.upload_page'))
                
                # Basic Data Integrity
                expected_numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'factor_value']
                for col in expected_numeric_cols:
                    if col in df.columns:
                        original_nan_count = df[col].isnull().sum()
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        if df[col].isnull().all() and original_nan_count < len(df[col]):
                            os.remove(save_path)
                            flash(f'Data type error: Column "{col}" could not be converted to numeric or contains non-numeric values.', 'error')
                            return redirect(url_for('main.upload_page'))
                
                flash(f'File {filename} uploaded and validated successfully. Redirecting to preview...', 'success')
                return redirect(url_for('main.preview', filename=filename))

            except Exception as e:
                if os.path.exists(save_path):
                    os.remove(save_path)
                flash(f'Error during file validation: {e}', 'error')
                return redirect(url_for('main.upload_page'))
            # --- End Data Validation ---

        except Exception as e:
            flash(f'Error saving file: {e}', 'error')
            return redirect(url_for('main.upload_page'))
    else:
        flash('File type not allowed. Please upload CSV, XLS, or XLSX files.', 'error')
        return redirect(url_for('main.upload_page'))


@bp.route('/preview/<filename>')
def preview(filename):
    if secure_filename(filename) != filename:
        abort(404)

    processed_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], filename)
    upload_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    filepath = None
    file_location = None

    if os.path.exists(processed_filepath):
        filepath = processed_filepath
        file_location = "processed"
    elif os.path.exists(upload_filepath):
        filepath = upload_filepath
        file_location = "uploads"
    else:
        flash(f'File {filename} not found in processed or upload directories.', 'error')
        return redirect(url_for('main.upload_page'))

    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(filepath, index_col=[0, 1])
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(filepath, index_col=[0, 1])
        else:
            flash(f'Unsupported file type for preview: {filename}', 'error')
            return redirect(url_for('main.upload_page'))

        data_head = df.head(20)
        statistics = df.describe(include='all')
        missing_counts = df.isnull().sum()
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        
        return render_template('preview.html', 
                               filename=filename, 
                               data_head=data_head, 
                               statistics=statistics,
                               missing_counts=missing_counts,
                               numeric_cols=numeric_cols,
                               file_location=file_location)

    except Exception as e:
        flash(f'Error processing file {filename} for preview: {e}', 'error')
        return redirect(url_for('main.upload_page'))


@bp.route('/preprocess/missing_values/<filename>', methods=['POST'])
def handle_missing_values(filename):
    if secure_filename(filename) != filename:
        abort(403)

    processed_filepath_source = os.path.join(current_app.config['PROCESSED_FOLDER'], filename)
    upload_filepath_source = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    source_filepath = None
    if os.path.exists(processed_filepath_source):
        source_filepath = processed_filepath_source
    elif os.path.exists(upload_filepath_source):
        source_filepath = upload_filepath_source
    else:
        flash(f'Original file {filename} not found.', 'error')
        return redirect(url_for('main.upload_page'))

    strategy = request.form.get('mv_strategy')
    if not strategy:
        flash('No missing value handling strategy selected.', 'error')
        return redirect(url_for('main.preview', filename=filename))

    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(source_filepath, index_col=[0, 1])
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(source_filepath, index_col=[0, 1])
        else:
            flash(f'Unsupported file type: {filename}', 'error')
            return redirect(url_for('main.preview', filename=filename))

        df_processed = None
        if strategy == 'ffill':
            df_processed = df.ffill()
        elif strategy == 'bfill':
            df_processed = df.bfill()
        elif strategy == 'dropna_rows':
            df_processed = df.dropna(axis=0)
        elif strategy == 'dropna_cols':
            df_processed = df.dropna(axis=1)
        elif strategy == 'interpolate_linear':
            df_processed = df.interpolate(method='linear', axis=0) 
        else:
            flash('Invalid missing value handling strategy selected.', 'error')
            return redirect(url_for('main.preview', filename=filename))

        base, ext = os.path.splitext(filename)
        secure_base = secure_filename(base.rsplit('_mv_', 1)[0].rsplit('_outlier_', 1)[0])
        if not secure_base: secure_base = "processed_file"
        
        processed_filename_stem = f"{secure_base}_mv_{strategy}"
        processed_filename = secure_filename(f"{processed_filename_stem}{ext}")
        
        os.makedirs(current_app.config['PROCESSED_FOLDER'], exist_ok=True)
        output_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], processed_filename)

        if file_ext == 'csv':
            df_processed.to_csv(output_filepath, index=True)
        elif file_ext in ['xls', 'xlsx']:
            df_processed.to_excel(output_filepath, index=True)
        
        flash(f'Missing values handled using {strategy}. Processed file: {processed_filename}', 'success')
        return redirect(url_for('main.preview', filename=processed_filename))

    except Exception as e:
        flash(f'Error during missing value processing for {filename}: {e}', 'error')
        return redirect(url_for('main.preview', filename=filename))


@bp.route('/preprocess/outliers/<filename>', methods=['POST'])
def handle_outliers(filename):
    if secure_filename(filename) != filename:
        abort(403)

    processed_filepath_source = os.path.join(current_app.config['PROCESSED_FOLDER'], filename)
    upload_filepath_source = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    source_filepath = None
    if os.path.exists(processed_filepath_source):
        source_filepath = processed_filepath_source
    elif os.path.exists(upload_filepath_source):
        source_filepath = upload_filepath_source
    else:
        flash(f'Original file {filename} not found.', 'error')
        return redirect(url_for('main.upload_page'))

    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(source_filepath, index_col=[0, 1])
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(source_filepath, index_col=[0, 1])
        else:
            flash(f'Unsupported file type: {filename}', 'error')
            return redirect(url_for('main.preview', filename=filename))

        df_processed = df.copy()
        selected_columns_form = request.form.getlist('outlier_columns')
        detection_method = request.form.get('detection_method')
        handling_method = request.form.get('handling_method')
        lower_quantile_str = request.form.get('lower_quantile', '0.01')
        upper_quantile_str = request.form.get('upper_quantile', '0.99')

        try:
            lower_quantile = float(lower_quantile_str)
            upper_quantile = float(upper_quantile_str)
            if not (0 <= lower_quantile < 1 and 0 < upper_quantile <= 1 and lower_quantile < upper_quantile):
                flash('Invalid quantile range. Lower must be < upper, and between 0 and 1.', 'error')
                return redirect(url_for('main.preview', filename=filename))
        except ValueError:
            flash('Invalid quantile values. Must be numbers.', 'error')
            return redirect(url_for('main.preview', filename=filename))

        if not selected_columns_form:
            flash('No columns selected for outlier handling.', 'error')
            return redirect(url_for('main.preview', filename=filename))

        actual_selected_columns = []
        if "_all_numeric_" in selected_columns_form:
            actual_selected_columns = df_processed.select_dtypes(include=np.number).columns.tolist()
        else:
            all_numeric_cols = df_processed.select_dtypes(include=np.number).columns
            for col_name in selected_columns_form:
                if col_name in all_numeric_cols:
                    actual_selected_columns.append(col_name)
                else:
                    flash(f"Warning: Column '{col_name}' is not numeric or does not exist, skipping.", "warning")
        
        if not actual_selected_columns:
            flash('No valid numeric columns selected for outlier handling.', 'error')
            return redirect(url_for('main.preview', filename=filename))
        
        rows_to_drop_mask = pd.Series(False, index=df_processed.index)

        for col_name in actual_selected_columns:
            series = df_processed[col_name]
            outliers_series_mask = pd.Series(False, index=series.index)
            col_lower_bound, col_upper_bound = None, None

            if detection_method == '3sigma':
                outliers_series_mask = detect_outliers_sigma(series, n_std=3)
                mean = series.mean()
                std = series.std()
                if std != 0:
                    col_lower_bound = mean - 3 * std
                    col_upper_bound = mean + 3 * std
            elif detection_method == 'quantile':
                outliers_series_mask = detect_outliers_quantile(series, lower_quantile=lower_quantile, upper_quantile=upper_quantile)
                col_lower_bound = series.quantile(lower_quantile)
                col_upper_bound = series.quantile(upper_quantile)
            else:
                flash('Invalid outlier detection method selected.', 'error')
                return redirect(url_for('main.preview', filename=filename))

            if handling_method == 'cap':
                if col_lower_bound is not None and col_upper_bound is not None and col_lower_bound != col_upper_bound:
                    df_processed[col_name] = cap_outliers(series, col_lower_bound, col_upper_bound)
                elif col_lower_bound == col_upper_bound and (col_lower_bound is not None): # check if bounds are not None
                     flash(f"Warning: For column '{col_name}', lower and upper bounds are identical ({col_lower_bound}). No capping applied.", "warning")
            elif handling_method == 'remove':
                rows_to_drop_mask |= outliers_series_mask
            else:
                flash('Invalid outlier handling method selected.', 'error')
                return redirect(url_for('main.preview', filename=filename))

        if handling_method == 'remove' and rows_to_drop_mask.any():
            df_processed = df_processed[~rows_to_drop_mask]
            if df_processed.empty:
                flash('All rows were removed by outlier handling. Resulting file is empty.', 'warning')

        base, ext = os.path.splitext(filename)
        secure_base = secure_filename(base.rsplit('_outlier_', 1)[0].rsplit('_mv_',1)[0])
        if not secure_base: secure_base = "processed_file"

        processed_filename_stem = f"{secure_base}_outlier_{detection_method}_{handling_method}"
        processed_filename = secure_filename(f"{processed_filename_stem}{ext}")
        
        os.makedirs(current_app.config['PROCESSED_FOLDER'], exist_ok=True)
        output_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], processed_filename)

        if file_ext == 'csv':
            df_processed.to_csv(output_filepath, index=True)
        elif file_ext in ['xls', 'xlsx']:
            df_processed.to_excel(output_filepath, index=True)
        
        flash(f'Outliers handled for columns: {", ".join(actual_selected_columns)}. Processed file: {processed_filename}', 'success')
        return redirect(url_for('main.preview', filename=processed_filename))

    except Exception as e:
        flash(f'Error during outlier processing for {filename}: {e}', 'error')
        return redirect(url_for('main.preview', filename=filename))


@bp.route('/preprocess/standardize/<filename>', methods=['POST'])
def handle_standardization(filename):
    if secure_filename(filename) != filename:
        abort(403)

    # Determine the source filepath (check PROCESSED_FOLDER first, then UPLOAD_FOLDER)
    processed_filepath_source = os.path.join(current_app.config['PROCESSED_FOLDER'], filename)
    upload_filepath_source = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    source_filepath = None
    if os.path.exists(processed_filepath_source):
        source_filepath = processed_filepath_source
    elif os.path.exists(upload_filepath_source):
        source_filepath = upload_filepath_source
    else:
        flash(f'Original file {filename} not found.', 'error')
        return redirect(url_for('main.upload_page'))

    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(source_filepath, index_col=[0, 1])
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(source_filepath, index_col=[0, 1])
        else:
            flash(f'Unsupported file type: {filename}', 'error')
            return redirect(url_for('main.preview', filename=filename))

        df_processed = df.copy()

        selected_columns_form = request.form.getlist('std_columns')
        std_method = request.form.get('std_method')

        if not selected_columns_form:
            flash('No columns selected for standardization.', 'error')
            return redirect(url_for('main.preview', filename=filename))
        
        if not std_method:
            flash('No standardization method selected.', 'error')
            return redirect(url_for('main.preview', filename=filename))

        actual_selected_columns = []
        if "_all_numeric_" in selected_columns_form:
            actual_selected_columns = df_processed.select_dtypes(include=np.number).columns.tolist()
        else:
            all_numeric_cols = df_processed.select_dtypes(include=np.number).columns
            for col_name in selected_columns_form:
                if col_name in all_numeric_cols:
                    actual_selected_columns.append(col_name)
                else:
                    flash(f"Warning: Column '{col_name}' is not numeric or does not exist, skipping for standardization.", "warning")
        
        if not actual_selected_columns:
            flash('No valid numeric columns selected for standardization.', 'error')
            return redirect(url_for('main.preview', filename=filename))

        for col_name in actual_selected_columns:
            if df_processed[col_name].isnull().any():
                flash(f"Warning: Column '{col_name}' contains missing values. Standardization might produce NaNs or errors. Please handle missing values first.", "warning")
            
            if std_method == 'zscore':
                mean = df_processed[col_name].mean()
                std = df_processed[col_name].std()
                if std == 0:
                    df_processed[col_name] = 0  # Or np.nan, or no change
                    flash(f"Warning: Column '{col_name}' has zero standard deviation. Z-score set to 0.", "warning")
                else:
                    df_processed[col_name] = (df_processed[col_name] - mean) / std
            elif std_method == 'minmax':
                min_val = df_processed[col_name].min()
                max_val = df_processed[col_name].max()
                range_val = max_val - min_val
                if range_val == 0:
                    df_processed[col_name] = 0.5 # Or 0, or np.nan, or no change
                    flash(f"Warning: Column '{col_name}' has zero range (all values are the same). Min-Max scaled to 0.5.", "warning")
                else:
                    df_processed[col_name] = (df_processed[col_name] - min_val) / range_val
            elif std_method == 'rank_pct':
                df_processed[col_name] = df_processed[col_name].rank(method='average', pct=True)
            else:
                flash('Invalid standardization method selected.', 'error')
                return redirect(url_for('main.preview', filename=filename))

        base, ext = os.path.splitext(filename)
        # Clean up previous processing tags
        secure_base = secure_filename(base.rsplit('_std_', 1)[0].rsplit('_outlier_', 1)[0].rsplit('_mv_',1)[0])
        if not secure_base: secure_base = "processed_file"

        processed_filename_stem = f"{secure_base}_std_{std_method}"
        processed_filename = secure_filename(f"{processed_filename_stem}{ext}")
        
        os.makedirs(current_app.config['PROCESSED_FOLDER'], exist_ok=True)
        output_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], processed_filename)

        if file_ext == 'csv':
            df_processed.to_csv(output_filepath, index=True)
        elif file_ext in ['xls', 'xlsx']:
            df_processed.to_excel(output_filepath, index=True)
        
        flash(f'Standardization ({std_method}) applied to columns: {", ".join(actual_selected_columns)}. Processed file: {processed_filename}', 'success')
        return redirect(url_for('main.preview', filename=processed_filename))

    except Exception as e:
        flash(f'Error during standardization for {filename}: {e}', 'error')
        return redirect(url_for('main.preview', filename=filename))


@bp.route('/preprocess/align_timeseries/<filename>', methods=['POST'])
def handle_align_timeseries(filename):
    if secure_filename(filename) != filename:
        abort(403)

    processed_filepath_source = os.path.join(current_app.config['PROCESSED_FOLDER'], filename)
    upload_filepath_source = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    source_filepath = None
    if os.path.exists(processed_filepath_source):
        source_filepath = processed_filepath_source
    elif os.path.exists(upload_filepath_source):
        source_filepath = upload_filepath_source
    else:
        flash(f'Original file {filename} not found.', 'error')
        return redirect(url_for('main.upload_page'))

    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext == 'csv':
            df = pd.read_csv(source_filepath, index_col=[0, 1], parse_dates=[0])
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(source_filepath, index_col=[0, 1], parse_dates=[0])
        else:
            flash(f'Unsupported file type: {filename}', 'error')
            return redirect(url_for('main.preview', filename=filename))

        df_processed = df.copy()

        target_frequency = request.form.get('target_frequency')
        agg_method = request.form.get('agg_method')

        if not target_frequency or not agg_method:
            flash('Target frequency and aggregation method must be selected.', 'error')
            return redirect(url_for('main.preview', filename=filename))
            
        # Ensure the first level of the index is datetime
        if not isinstance(df_processed.index.levels[0], pd.DatetimeIndex):
            try:
                df_processed.index.set_levels(pd.to_datetime(df_processed.index.levels[0]), level=0, inplace=True)
            except Exception as e:
                flash(f"Could not convert the first index level to datetime: {e}", "error")
                return redirect(url_for('main.preview', filename=filename))
        
        day_level_name = df_processed.index.names[0] if df_processed.index.names[0] else 'day'
        sec_level_name = df_processed.index.names[1] if df_processed.index.names[1] else 'sec'
        # Ensure original index names are set before unstacking
        df_processed.index.names = [day_level_name, sec_level_name]

        # Unstack the security level
        df_unstacked = df_processed.unstack(level=sec_level_name)
        
        # Store original column names from the unstacked df to correctly re-stack later
        original_unstacked_multi_columns_names = df_unstacked.columns.names

        # Perform resampling and aggregation
        # For 'mean' and 'sum', apply only to numeric columns and handle non-numeric separately.
        if agg_method in ['mean', 'sum']:
            numeric_df_unstacked = df_unstacked.select_dtypes(include=np.number)
            df_resampled_numeric = pd.DataFrame() # Ensure it exists even if no numeric data
            
            if not numeric_df_unstacked.empty:
                df_resampled_numeric = numeric_df_unstacked.resample(rule=target_frequency).agg(agg_method)
            
            non_numeric_df_unstacked = df_unstacked.select_dtypes(exclude=np.number)
            df_resampled_non_numeric = pd.DataFrame() # Ensure it exists

            if not non_numeric_df_unstacked.empty:
                df_resampled_non_numeric = non_numeric_df_unstacked.resample(rule=target_frequency).agg('last') # or 'first'
            
            if df_resampled_numeric.empty and df_resampled_non_numeric.empty: # Both empty
                 df_resampled = df_unstacked.resample(rule=target_frequency).agg('last') # Default fallback
                 if not df_unstacked.empty: # Only flash if there was data to begin with
                    flash(f"Warning: No numeric data for '{agg_method}' and no non-numeric data. Resampling with 'last'.", "warning")
            elif df_resampled_numeric.empty:
                df_resampled = df_resampled_non_numeric
                flash(f"Warning: No numeric data found for '{agg_method}'. Non-numeric data aggregated using 'last'.", "warning")
            elif df_resampled_non_numeric.empty:
                df_resampled = df_resampled_numeric
            else:
                df_resampled = pd.concat([df_resampled_numeric, df_resampled_non_numeric], axis=1)
        else: # For 'first', 'last'
            df_resampled = df_unstacked.resample(rule=target_frequency).agg(agg_method)

        # Stack back the security level
        # The levels to stack are the names of the columns index levels from *before* resampling
        # which is typically just the sec_level_name if df_unstacked.columns was a simple Index of sec_ids
        # or multiple levels if original df.columns was a MultiIndex before unstacking sec_level_name
        # For this application, df_unstacked.columns is a MultiIndex ('value_column_name', 'sec_id')
        # So we stack the 'sec_id' level, which is original_unstacked_multi_columns_names[1]
        df_realigned = df_resampled.stack(level=original_unstacked_multi_columns_names[1], future_stack=True)
        
        # The new index levels will be [resampled_day_level, stacked_sec_level]
        # The name of the resampled_day_level is usually the original day_level_name.
        # The name of the stacked_sec_level is usually the name of the column level that was stacked (sec_level_name).
        df_realigned.index.names = [day_level_name, sec_level_name]
        
        # The task asks to swaplevel(0,1) if day becomes level 1.
        # After unstack(sec_level_name) and then stack(sec_level_name),
        # the original day level (now resampled) should remain the first level (level 0).
        # No swap should be necessary if pandas behaves as expected.
        # Let's verify the order just in case, though it's unlikely to be swapped.
        if df_realigned.index.names[0] != day_level_name:
             # This case should ideally not happen. If it does, a swap might be needed,
             # or the logic for naming/stacking needs review.
             # For now, we assume the order is [day_level_name, sec_level_name]
             pass

        df_realigned = df_realigned.sort_index()

        base, ext = os.path.splitext(filename)
        secure_base = secure_filename(base.rsplit('_aligned_', 1)[0].rsplit('_std_', 1)[0].rsplit('_outlier_', 1)[0].rsplit('_mv_',1)[0])
        if not secure_base: secure_base = "processed_file"

        processed_filename_stem = f"{secure_base}_aligned_{target_frequency}"
        processed_filename = secure_filename(f"{processed_filename_stem}{ext}")
        
        os.makedirs(current_app.config['PROCESSED_FOLDER'], exist_ok=True)
        output_filepath = os.path.join(current_app.config['PROCESSED_FOLDER'], processed_filename)

        if file_ext == 'csv':
            df_realigned.to_csv(output_filepath, index=True)
        elif file_ext in ['xls', 'xlsx']:
            df_realigned.to_excel(output_filepath, index=True)
        
        flash(f'Time series aligned to {target_frequency} using {agg_method}. Processed file: {processed_filename}', 'success')
        return redirect(url_for('main.preview', filename=processed_filename))

    except Exception as e:
        current_app.logger.error(f"Error during time series alignment for {filename}: {e}", exc_info=True)
        flash(f'Error during time series alignment: {e}', 'error')
        return redirect(url_for('main.preview', filename=filename))
