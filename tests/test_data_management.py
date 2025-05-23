import os
import shutil
import tempfile
import unittest
import pandas as pd
import numpy as np
from io import BytesIO
from app import create_app, Config
from werkzeug.datastructures import FileStorage

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False # Disable CSRF for simpler form testing in unit tests

class DataManagementTestCase(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for uploads and processed files
        self.temp_upload_dir = tempfile.mkdtemp()
        self.temp_processed_dir = tempfile.mkdtemp()

        # Configure app with temporary directories
        self.app = create_app(TestConfig)
        self.app.config['UPLOAD_FOLDER'] = self.temp_upload_dir
        self.app.config['PROCESSED_FOLDER'] = self.temp_processed_dir
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Remove temporary directories
        shutil.rmtree(self.temp_upload_dir)
        shutil.rmtree(self.temp_processed_dir)
        self.app_context.pop()

    def _create_dummy_dataframe(self, data_dict, index_names=['day', 'sec']):
        """
        Creates a DataFrame from a dictionary with MultiIndex.
        Keys of data_dict are tuples for MultiIndex, values are dicts for columns.
        Example: {('2023-01-01', 'AAPL'): {'open': 150, 'close': 151}}
        """
        # Reformat data_dict for DataFrame.from_dict
        # Pandas from_dict with orient='index' expects: {idx: {col: val}}
        # If MultiIndex, idx is a tuple.
        df = pd.DataFrame.from_dict(data_dict, orient='index')
        if not df.empty:
            df.index = pd.MultiIndex.from_tuples(df.index, names=index_names)
        return df

    def _create_dummy_file(self, filename, data_dict, index_names=['day', 'sec'], parse_dates_on_index_level=0):
        """
        Creates a dummy CSV or XLSX file in the UPLOAD_FOLDER.
        Returns the full path to the created file.
        """
        df = self._create_dummy_dataframe(data_dict, index_names)
        
        # Convert the specified index level to datetime if requested and possible
        if parse_dates_on_index_level is not None and not df.empty and df.index.nlevels > parse_dates_on_index_level:
            try:
                current_level_values = df.index.get_level_values(parse_dates_on_index_level)
                # Only attempt conversion if not already datetime
                if not pd.api.types.is_datetime64_any_dtype(current_level_values):
                    new_level_values = pd.to_datetime(current_level_values)
                    # Create new index with the converted level
                    levels = list(df.index.levels)
                    levels[parse_dates_on_index_level] = new_level_values
                    # If codes are needed (pandas < some version)
                    # codes = list(df.index.codes)
                    # df.index = pd.MultiIndex(levels=levels, codes=codes, names=df.index.names)
                    # More robust way for newer pandas:
                    new_index_tuples = []
                    for tup in df.index:
                        new_tup_list = list(tup)
                        new_tup_list[parse_dates_on_index_level] = pd.to_datetime(new_tup_list[parse_dates_on_index_level])
                        new_index_tuples.append(tuple(new_tup_list))
                    df.index = pd.MultiIndex.from_tuples(new_index_tuples, names=df.index.names)

            except Exception as e:
                print(f"Warning: Could not convert index level {parse_dates_on_index_level} to datetime during dummy file creation: {e}")


        filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
        
        if filename.endswith('.csv'):
            df.to_csv(filepath, index=True)
        elif filename.endswith('.xlsx'):
            df.to_excel(filepath, index=True)
        else:
            raise ValueError("Unsupported file extension for dummy file.")
            
        return filepath

    # --- Placeholder for tests ---
    def test_example(self): # A simple test to ensure setup is working
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
