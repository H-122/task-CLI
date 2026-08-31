import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import date, timedelta, time, datetime
from zoneinfo import ZoneInfo

oggi = date.today().strftime("%Y-%m-%d")
dopodomani = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 45.5663,
    "longitude": 5.9208,
    "hourly": ["precipitation_probability", "precipitation", "apparent_temperature"],
    "start_date": oggi,
    "end_date": dopodomani,
    "timezone": "auto",
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_precipitation_probability = hourly.Variables(0).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()

hourly_data = {
    "date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )
}

hourly_data["precipitation"] = hourly_precipitation
hourly_data["precipitation_probability"] = hourly_precipitation_probability
hourly_data["apparent_temperature"] = hourly_apparent_temperature

hourly_dataframe = pd.DataFrame(data=hourly_data)

# Che ore sono adesso a Chambéry, e quante ore selezionare
ora_locale = datetime.now(ZoneInfo("Europe/Paris"))

if time(5, 0) <= ora_locale.time() < time(8, 0):
    ore_da_selezionare = 24
elif time(17, 30) <= ora_locale.time() < time(19, 0):
    ore_da_selezionare = 36
else:
    # Fuori da queste due fasce (es. stai testando lo script a mano in un altro orario):
    # per ora scelgo 24 come comportamento di default.
    ore_da_selezionare = 24

# Filtrare il DataFrame per prendere solo le prossime N ore
hourly_dataframe["date"] = hourly_dataframe["date"].dt.tz_convert("Europe/Paris")

inizio_finestra = ora_locale.replace(minute=0, second=0, microsecond=0)
fine_finestra = inizio_finestra + timedelta(hours=ore_da_selezionare)

finestra = hourly_dataframe[
    (hourly_dataframe["date"] >= inizio_finestra) &
    (hourly_dataframe["date"] < fine_finestra)
].reset_index(drop=True)


def emoji_probabilita(probabilita, ora):
    if probabilita >= 30:
        return "🌧️"
    elif 6 <= ora < 19:
        return "☀️"
    else:
        return "🌙"


def emoji_intensita(mm):
    if mm <= 0:
        return f"{mm:.1f}mm"
    elif mm <= 1:
        return f"{mm:.1f}mm 💧 leggera"
    elif mm <= 4:
        return f"{mm:.1f}mm 💦 media"
    elif mm <= 10:
        return f"{mm:.1f}mm ⛈️ forte"
    else:
        return f"{mm:.1f}mm 🌊 fortissima"


righe = []
for _, riga in finestra.iterrows():
    colonna_orario = riga["date"].strftime("%d/%m %H:%M")
    colonna_probabilita = f"{riga['precipitation_probability']:.0f}% {emoji_probabilita(riga['precipitation_probability'], riga['date'].hour)}"
    colonna_temperatura = f"{round(riga['apparent_temperature'])}°C"
    colonna_intensita = emoji_intensita(riga['precipitation'])

    righe.append([colonna_orario, colonna_probabilita, colonna_temperatura, colonna_intensita])

tabella = pd.DataFrame(righe, columns=["Orario", "Probabilità pioggia", "Temperatura", "Intensità precipitazioni (se succede)"])
print(tabella.to_string(index=False))