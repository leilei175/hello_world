# Data Management Tool

A Flask-based web application for uploading, processing, and managing data files.

## Project Structure

```
.
├── app/                      # Main application folder
│   ├── __init__.py           # Application factory
│   ├── routes.py             # Web page routes
│   ├── models.py             # Data models (currently empty)
│   ├── forms.py              # Web forms (currently empty)
│   ├── utils.py              # Utility functions (currently empty)
│   ├── static/               # Static assets
│   │   ├── css/              # Stylesheets
│   │   ├── js/               # JavaScript files
│   │   └── img/              # Image files
│   └── templates/            # HTML templates
│       ├── base.html         # Base HTML template
│       ├── index.html        # Main page template
│       └── upload.html       # File upload page template
├── data/                     # Data storage
│   ├── uploads/              # Raw uploaded files
│   └── processed/            # Processed data files
├── tests/                    # Unit tests
│   ├── __init__.py
│   └── test_data_management.py # Tests for data management (currently empty)
├── config.py                 # Application configuration
├── run.py                    # Script to run the Flask development server
├── requirements.txt          # Project dependencies
├── .gitignore                # Git ignore file
└── README.md                 # This file
```

## Setup and Run

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python run.py
    ```
    The application will be accessible at `http://127.0.0.1:5000/`.

## Usage

-   Navigate to the homepage to see a welcome message.
-   Go to the "Upload Data" page to upload CSV, XLS, or XLSX files.

(Further details on processing and management features will be added as they are developed.)
