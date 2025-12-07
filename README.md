# Weather Forecast - ML Predictor

A Flask-based weather forecast application that combines real-time weather data from OpenWeatherMap API with machine learning to predict tomorrow's temperature.

## Features

- 🌤️ Real-time weather data from OpenWeatherMap API
- 🤖 ML-powered temperature prediction using Linear Regression
- 🎨 Modern, responsive UI with real-time search
- 📊 Display of current weather metrics (temperature, humidity, wind speed, clouds)
- 🔄 JSON API endpoint for programmatic access

## Tech Stack

- **Backend**: Flask (Python web framework)
- **ML**: scikit-learn (Linear Regression model)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **External API**: OpenWeatherMap

## Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/weather-forecast.git
   cd weather-forecast
   ```

2. **Create a virtual environment**
   ```powershell
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   
   ```bash
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Key**
   - Copy `.env.example` to `.env`
   - Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
   - Add your API key to `.env`

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   - Navigate to `http://localhost:5000`

## Usage

1. Enter a city name in the search box (e.g., "Delhi", "New York", "London")
2. Click "Get Forecast" or press Enter
3. View current weather data and ML-predicted temperature for tomorrow

## API Endpoints

### GET `/`
Returns the main weather forecast page.

### POST `/get_weather`
Fetches weather data and returns JSON response.

**Parameters:**
- `city` (string): City name to search

**Response:**
```json
{
  "city": "Delhi",
  "temp": 28,
  "humidity": 65,
  "description": "Clear sky",
  "predicted_temp": 29,
  "icon_url": "..."
}
```

## Project Structure

```
weather-forecast/
├── app.py                 # Flask application & ML model
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   ├── images/           # Background images
│   └── js/
│       └── app.js        # Frontend logic
├── templates/
│   └── index.html        # HTML template
└── Bgimg/                # Background image assets
```

## Machine Learning Model

The application uses a simple Linear Regression model trained on sample temperature and humidity data to predict tomorrow's temperature. The model:
- Takes today's temperature and humidity as input
- Outputs predicted temperature for tomorrow
- Can be replaced with a more sophisticated model or pre-trained model

To improve predictions:
1. Collect more historical data
2. Add additional features (pressure, wind speed, season, etc.)
3. Try advanced algorithms (Random Forest, Neural Networks, etc.)
4. Implement cross-validation and hyperparameter tuning

## Environment Variables

Create a `.env` file (use `.env.example` as template):
```
OPENWEATHER_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Author

Developed by Ayush Singh

## Disclaimer

- This application is for educational and demonstration purposes
- The ML model is a simplified example and should not be used for critical weather predictions
- Ensure you have a valid OpenWeatherMap API key before running the application
- Respect OpenWeatherMap API rate limits and terms of service
