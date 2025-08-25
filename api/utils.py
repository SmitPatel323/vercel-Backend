import os
import pickle 
import numpy as np
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline


MODEL_DIR = os.path.join(os.path.dirname(__file__), 'ml_models')
TIME_MODEL_PATH = os.path.join(MODEL_DIR, 'delivery_time_model.pkl')
COST_MODEL_PATH = os.path.join(MODEL_DIR, 'maintenance_cost_model.pkl')

def ensure_model_dir_exists():
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

def train_and_save_models():
    ensure_model_dir_exists()

    if not os.path.exists(TIME_MODEL_PATH):
        print("Training Delivery Time model...")
        X_time = np.array([10, 25, 50, 80, 100, 150, 200]).reshape(-1, 1)
        y_time = np.array([0.5, 1.1, 2.0, 3.5, 4.2, 6.8, 9.0])
        time_model_pipeline = Pipeline([
            ("poly_features", PolynomialFeatures(degree=2, include_bias=False)),
            ("lin_reg", LinearRegression()),
        ])
        time_model_pipeline.fit(X_time, y_time)
        
        with open(TIME_MODEL_PATH, 'wb') as f:
            pickle.dump(time_model_pipeline, f)
        print("Delivery Time model trained and saved as .pkl.")

    if not os.path.exists(COST_MODEL_PATH):
        print("Training Maintenance Cost model...")
        X_cost = np.array([[1, 20000], [2, 45000], [3, 60000], [4, 85000], [5, 110000]])
        y_cost = np.array([150, 320, 480, 700, 950])
        cost_model = LinearRegression()
        cost_model.fit(X_cost, y_cost)
        
        with open(COST_MODEL_PATH, 'wb') as f:
            pickle.dump(cost_model, f)
        print("Maintenance Cost model trained and saved as .pkl.")

#intercept=0.1892,linearCoeff=0.0195,quadraCoeff=0.00011
def predict_delivery_time(distance_km):      #PredictedTime = intercept+(linearCoeff*dist)+(quadraCoeff*dist²)
    """Loads the time prediction model and predicts delivery time."""
    if distance_km < 20:
        return (distance_km / 30.0) + 0.17
    
    if not os.path.exists(TIME_MODEL_PATH):
        return (distance_km / 40.0)

   
    with open(TIME_MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    predicted_time = model.predict(np.array([[distance_km]]))
    return predicted_time[0]

#intercept=155.51,ageCoeff=-20.45,mileageCoeff=0.0082
def predict_maintenance_cost(vehicle_age_years, distance_covered_km):  #PredictedCost =intercept+(ageCoeff*avgAge)+(MileageCoeff*avg_Mileage)
    """Loads the cost prediction model and predicts maintenance cost."""
    if distance_covered_km < 10000:
        return 50 + (distance_covered_km * 0.01)

    if not os.path.exists(COST_MODEL_PATH):
        return 100 + (vehicle_age_years * 50)

    with open(COST_MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    predicted_cost = model.predict(np.array([[vehicle_age_years, distance_covered_km]]))
    
    return max(50, predicted_cost[0])


def get_weather_forecast(city):
    if not city:
        return "N/A"
    
    api_key = settings.WEATHER_API_KEY
    if not api_key:
        print("ERROR: WEATHER_API_KEY not set in settings.py")
        return "API key missing"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() 
        data = response.json()

        if data.get("weather"):
            temp = data['main']['temp']
            description = data['weather'][0]['description'].title()
            return f"{temp}°C, {description}"
        else:
            return "Forecast unavailable"

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather from API: {e}")
        return "Forecast unavailable"
