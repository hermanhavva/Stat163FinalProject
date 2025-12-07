import pandas as pd
import geopandas as gpd
import altair as alt

# 1. Вхідні дані: Координати центрів повітів (вже конвертовані в float)
# Порядок у GeoPandas: Longitude (X), Latitude (Y)
data = [
    {"name": "Золотоніський", "lat": 49.6689, "lon": 32.0475},
    {"name": "Гадяцький",     "lat": 50.3678, "lon": 33.9797}, # Виправлено з 34.0 для точності центру
    {"name": "Зіньківський",  "lat": 50.2046, "lon": 34.3639},
    {"name": "Кобеляцький",   "lat": 49.1430, "lon": 34.2000},
    {"name": "Костянтиноградський", "lat": 49.3717, "lon": 35.4567},
    {"name": "Кременчуцький", "lat": 49.0658, "lon": 33.4100}, # Уточнено
    {"name": "Лохвицький",    "lat": 50.3578, "lon": 33.2658},
    {"name": "Лубенський",    "lat": 50.0161, "lon": 32.9886},
    {"name": "Миргородський", "lat": 49.9658, "lon": 33.6114},
    {"name": "Переяславський", "lat": 50.0661, "lon": 31.4422}, # Виправлено опечатку в назві
    {"name": "Полтавський",   "lat": 49.5894, "lon": 34.5511},
    {"name": "Прилуцький",    "lat": 50.5885, "lon": 32.3876},
    {"name": "Пирятинський",  "lat": 50.2395, "lon": 32.5071},
    {"name": "Роменський",    "lat": 50.7428, "lon": 33.4878},
    {"name": "Хорольський",   "lat": 49.7822, "lon": 33.2741}
]

df_cities = pd.DataFrame(data)

# Створюємо GeoDataFrame для точок (вказуємо, що координати - це широта/довгота WGS84)
gdf_cities = gpd.GeoDataFrame(
    df_cities, 
    geometry=gpd.points_from_xy(df_cities.lon, df_cities.lat),
    crs="EPSG:4326"
)

# 2. Завантажуємо ваші намальовані полігони
input_geojson = 'poltava_regions.geojson'

try:
    gdf_polygons = gpd.read_file(input_geojson)
    # Переконуємось, що система координат співпадає
    if gdf_polygons.crs is None:
        gdf_polygons.set_crs("EPSG:4326", allow_override=True, inplace=True)
except Exception as e:
    print(f"Помилка відкриття файлу {input_geojson}: {e}")
    exit()

# 3. SPATIAL JOIN: Присвоюємо імена полігонам
# "left" означає: залишити всі полігони, навіть якщо в них не потрапило місто (буде NaN)
gdf_merged = gpd.sjoin(gdf_polygons, gdf_cities, how="left", predicate="contains")

# Перевірка на "сиріт" (полігони без назви)
missing = gdf_merged[gdf_merged['name'].isna()]
if not missing.empty:
    print(f"УВАГА: {len(missing)} полігонів не отримали назву (місто не потрапило всередину).")
    print("Можливо, кордони намальовані неточно або центр міста опинився на межі.")

# Чистимо дані (видаляємо зайві колонки від join)
final_gdf = gdf_merged[['geometry', 'name']].copy()
final_gdf['id'] = final_gdf.index # ID для унікальності в Altair

# збережемо підписаний GeoJSON для майбутнього використання
output_geojson = 'poltava_governorate_named.geojson'
final_gdf.to_file(output_geojson, driver='GeoJSON')
print(f"Також збережено розмічений файл: '{output_geojson}'")