from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import time
from datetime import datetime, timedelta
import requests
import numpy as np
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ==========================
# 1. SIMPLE ML MODEL (AI PART)
# ==========================
# Toy training data:
# Features = [today_temp, today_humidity]
# Target   = tomorrow_temp
X_train = np.array([
    [30, 40],
    [32, 35],
    [35, 30],
    [25, 60],
    [28, 55],
    [22, 70],
    [20, 80],
    [27, 50],
    [29, 45],
    [24, 65]
])
y_train = np.array([31, 33, 36, 26, 29, 23, 21, 28, 30, 25])

model = LinearRegression()
model.fit(X_train, y_train)


OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
ONECALL_TIMEMACHINE = "https://api.openweathermap.org/data/2.5/onecall/timemachine"


def get_current_weather(city_name):
    """
    Calls OpenWeather API and returns:
    (temperature, humidity, description, feels_like, icon_url, error_message, metrics)

    `metrics` is a dict with keys like `clouds`, `wind_speed`, `rain_1h` (values may be None).
    """
    params = {
        "q": city_name,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=5)
    except requests.exceptions.RequestException as e:
        return None, None, None, None, None, f"Network error: {e}", None

    if response.status_code != 200:
        data = response.json()
        return None, None, None, None, None, data.get("message", "API error"), None

    data = response.json()
    main = data.get("main", {})
    weather_list = data.get("weather", [])
    weather = weather_list[0] if weather_list else {}

    temp = main.get("temp")
    humidity = main.get("humidity")
    feels_like = main.get("feels_like")
    description = weather.get("description", "").title()
    icon_code = weather.get("icon", "")
    icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ""

    # additional metrics for charts
    clouds = data.get('clouds', {}).get('all') if data.get('clouds') else None
    wind_speed = data.get('wind', {}).get('speed') if data.get('wind') else None
    # precipitation (rain or snow) in last 1 hour if reported
    rain_1h = None
    if data.get('rain') and isinstance(data.get('rain'), dict):
        rain_1h = data.get('rain').get('1h') or data.get('rain').get('3h')
    if rain_1h is None and data.get('snow') and isinstance(data.get('snow'), dict):
        rain_1h = data.get('snow').get('1h') or data.get('snow').get('3h')

    metrics = {
        'clouds': clouds,
        'wind_speed': wind_speed,
        'precipitation_1h': rain_1h
    }

    return temp, humidity, description, feels_like, icon_url, None, metrics


def get_multi_day_forecast(city_name, days=4):
    """Fetch 5-day / 3-hour forecast from OpenWeather and aggregate into daily values.
    Returns (daily_list, error_message) where daily_list is a list of dicts:
      {date: 'YYYY-MM-DD', avg_temp, avg_humidity, description, icon_url}
    """
    params = {
        "q": city_name,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }

    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=6)
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"

    if resp.status_code != 200:
        try:
            data = resp.json()
            return None, data.get("message", "API error")
        except Exception:
            return None, f"API error: status {resp.status_code}"

    data = resp.json()
    items = data.get("list", [])
    if not items:
        return None, "No forecast data returned"

    # group by date
    from collections import defaultdict, Counter
    groups = defaultdict(list)
    for it in items:
        dt_txt = it.get("dt_txt", "")
        date = dt_txt.split(" ")[0] if dt_txt else None
        if date:
            groups[date].append(it)

    # sort dates and compute aggregates
    dates = sorted(groups.keys())
    daily = []
    for date in dates[:days]:
        entries = groups[date]
        temps = [e.get("main", {}).get("temp") for e in entries if e.get("main")]
        hums = [e.get("main", {}).get("humidity") for e in entries if e.get("main")]
        weathers = [e.get("weather", [{}])[0] for e in entries]
        avg_temp = round(sum(temps) / len(temps), 2) if temps else None
        avg_hum = int(sum(hums) / len(hums)) if hums else None

        # most common description
        descs = [w.get("description", "") for w in weathers]
        desc_counter = Counter(descs)
        most_common_desc = desc_counter.most_common(1)[0][0].title() if descs else ""

        # try to pick an icon near midday (12:00) else first
        icon = ""
        icon_code = None
        mid = None
        for e in entries:
            if e.get("dt_txt", "").endswith("12:00:00"):
                mid = e
                break
        pick = mid or entries[0]
        icon_code = (pick.get("weather", [{}])[0] or {}).get("icon", "")
        icon = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ""

        daily.append({
            "date": date,
            "avg_temp": avg_temp,
            "avg_humidity": avg_hum,
            "description": most_common_desc,
            "icon_url": icon
        })

    return daily, None



def predict_tomorrow_temperature(today_temp, today_humidity):
    """
    Uses the trained ML model to predict tomorrow's temperature.
    """
    features = np.array([[today_temp, today_humidity]])
    predicted_temp = model.predict(features)[0]
    return float(predicted_temp)


def get_coords(city_name):
    """Return (lat, lon, error_message) for a given city using the basic weather endpoint."""
    params = {
        "q": city_name,
        "appid": OPENWEATHER_API_KEY
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=6)
    except requests.exceptions.RequestException as e:
        return None, None, f"Network error: {e}"

    if r.status_code != 200:
        try:
            return None, None, r.json().get('message', f'API error {r.status_code}')
        except Exception:
            return None, None, f'API error: status {r.status_code}'

    data = r.json()
    coord = data.get('coord') or {}
    lat = coord.get('lat')
    lon = coord.get('lon')
    if lat is None or lon is None:
        return None, None, 'Could not determine coordinates for city.'
    return lat, lon, None


def get_past_week(city_name, days=7):
    """Fetch average temperature for each of the past `days` days using OpenWeather timemachine.
    Returns (past_list, error_message)
    Each item in past_list: {date: 'YYYY-MM-DD', avg_temp: float, avg_temp_f: float}
    If the One Call timemachine calls fail (e.g., not available on the account), returns ([], err_message).
    """
    lat, lon, err = get_coords(city_name)
    if err is not None:
        return None, err

    past = []
    for i in range(1, days + 1):
        # timestamp for the target day (UTC) at roughly midday
        dt = int((datetime.utcnow() - timedelta(days=i)).replace(hour=12, minute=0, second=0, microsecond=0).timestamp())
        params = {
            'lat': lat,
            'lon': lon,
            'dt': dt,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        try:
            r = requests.get(ONECALL_TIMEMACHINE, params=params, timeout=8)
        except requests.exceptions.RequestException as e:
            return None, f"Network error while fetching historical data: {e}"

        if r.status_code != 200:
            # If any single day fails due to permissions (403) or other API errors, abort and return error
            try:
                msg = r.json().get('message', f'status {r.status_code}')
            except Exception:
                msg = f'status {r.status_code}'
            return None, f'Historical API error: {msg}'

        data = r.json()
        # timemachine returns hourly array for that day
        hours = data.get('hourly') or []
        temps = [h.get('temp') for h in hours if isinstance(h.get('temp'), (int, float))]
        if not temps:
            # try fallback to 'current' field
            current_temp = data.get('current', {}).get('temp')
            if current_temp is not None:
                avg_temp = float(current_temp)
            else:
                avg_temp = None
        else:
            avg_temp = round(sum(temps) / len(temps), 2)

        date_str = datetime.utcfromtimestamp(dt).strftime('%Y-%m-%d')
        past.append({
            'date': date_str,
            'avg_temp': avg_temp,
            'avg_temp_f': round(avg_temp * 9.0 / 5.0 + 32, 2) if avg_temp is not None else None
        })

        # be kind to the API (small pause)
        time.sleep(0.2)

    return past, None


# ==========================
# 3. FLASK ROUTE
# ==========================
@app.route("/", methods=["GET", "POST"])
def home():
    weather_data = None
    error_message = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()

        if not city:
            error_message = "Please enter a city name."
        else:
            temp, humidity, description, feels_like, icon_url, err, metrics = get_current_weather(city)


            if err is not None:
                error_message = err
            else:
                predicted_temp = predict_tomorrow_temperature(temp, humidity)

                weather_data = {
                    "city": city.title(),
                    "temp": round(temp, 2),
                    "temp_f": round(temp * 9.0 / 5.0 + 32, 2) if temp is not None else None,
                    "humidity": humidity,
                    "description": description,
                    "predicted_temp": round(predicted_temp, 2),
                    "predicted_temp_f": round(predicted_temp * 9.0 / 5.0 + 32, 2) if predicted_temp is not None else None,
                    "feels_like": round(feels_like, 2),
                    "feels_like_f": round(feels_like * 9.0 / 5.0 + 32, 2) if feels_like is not None else None,
                    "icon_url": icon_url,
                    "metrics": metrics
                }

    # Your index.html already understands:
    # {{ weather_data.city }}, {{ weather_data.temp }}, {{ weather_data.predicted_temp }}
    # Extra fields like humidity/description are just ignored if not used.
    return render_template("index.html",
                           weather_data=weather_data,
                           error_message=error_message)


@app.route('/api/forecast', methods=['POST'])
def api_forecast():
    """API endpoint that returns JSON for the frontend to consume.
    Expects JSON with: { "city": "CityName" }
    """
    data = None
    try:
        data = request.get_json(force=True)
    except Exception:
        # fall back to form data
        data = request.form or {}

    city = (data or {}).get('city', '').strip()

    if not city:
        return jsonify({"success": False, "error": "Please provide a city name."}), 400

    # get current weather
    temp, humidity, description, feels_like, icon_url, err, metrics = get_current_weather(city)

    if err is not None:
        return jsonify({"success": False, "error": err}), 500

    # get multi-day aggregated forecast (next few days)
    days = 4
    try:
        days = int(request.args.get('days', days))
    except Exception:
        days = 4

    daily, ferr = get_multi_day_forecast(city, days=days)
    if ferr is not None:
        # non-fatal: still return current + prediction for tomorrow only
        daily = []

    # Build predictions for each day using the toy model iteratively where possible
    predictions = []
    # first prediction: tomorrow based on current temp/humidity
    try:
        pred0 = predict_tomorrow_temperature(temp, humidity)
    except Exception:
        pred0 = None

    # assemble daily list to include predicted_temp field
    enhanced_daily = []
    for i, d in enumerate(daily):
        # use the day's avg_humidity for prediction where available
        hum = d.get('avg_humidity') or humidity
        # for temp input, if i==0 (tomorrow), use current temp, else use previous predicted temp if available
        if i == 0:
            temp_input = temp
        else:
            temp_input = enhanced_daily[i-1].get('predicted_temp') or d.get('avg_temp') or temp

        try:
            p = predict_tomorrow_temperature(temp_input, hum)
            p = round(p, 2)
        except Exception:
            p = None

        item = dict(d)
        item['predicted_temp'] = p
        # add Fahrenheit conversions where applicable
        try:
            item['avg_temp_f'] = round(item['avg_temp'] * 9.0 / 5.0 + 32, 2) if item.get('avg_temp') is not None else None
        except Exception:
            item['avg_temp_f'] = None
        try:
            item['predicted_temp_f'] = round(p * 9.0 / 5.0 + 32, 2) if p is not None else None
        except Exception:
            item['predicted_temp_f'] = None
        enhanced_daily.append(item)

    # fallback single prediction if no daily data
    if not enhanced_daily:
        enhanced_daily = []
        if pred0 is not None:
            enhanced_daily.append({
                "date": "tomorrow",
                "avg_temp": None,
                "avg_humidity": None,
                "description": "",
                "icon_url": "",
                "predicted_temp": round(pred0, 2),
                "predicted_temp_f": round(pred0 * 9.0 / 5.0 + 32, 2)
            })

    weather_data = {
        "city": city.title(),
        "temp": round(temp, 2),
        "temp_f": round(temp * 9.0 / 5.0 + 32, 2) if temp is not None else None,
        "humidity": humidity,
        "description": description,
        "predicted_temp": round(pred0, 2) if pred0 is not None else None,
        "predicted_temp_f": round(pred0 * 9.0 / 5.0 + 32, 2) if pred0 is not None else None,
        "feels_like": round(feels_like, 2),
        "feels_like_f": round(feels_like * 9.0 / 5.0 + 32, 2) if feels_like is not None else None,
        "icon_url": icon_url,
        "daily": enhanced_daily,
        "metrics": metrics
    }

    # attempt to fetch past week historical averages (non-fatal)
    try:
        past_week, perr = get_past_week(city, days=7)
    except Exception as e:
        past_week, perr = None, f"Internal error: {e}"

    if perr is not None:
        # don't fail the whole response for historical API issues
        weather_data['past_week'] = []
        weather_data['past_error'] = perr
    else:
        weather_data['past_week'] = past_week or []

    return jsonify({"success": True, "weather_data": weather_data})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)


@app.route('/bgimg/<path:filename>')
def serve_bgimg(filename):
    """Serve background images placed in the project `Bgimg` folder.
    This keeps the original image in place while making it accessible to the frontend.
    """
    # compute absolute path to the Bgimg folder next to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_dir = os.path.join(base_dir, '..', 'Bgimg')
    bg_dir = os.path.normpath(bg_dir)
    return send_from_directory(bg_dir, filename)
