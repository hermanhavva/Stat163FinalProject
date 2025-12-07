import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import json
import os
import sys
from PIL import Image

# ==========================================
# КОНФІГУРАЦІЯ (ЗАПОВНІТЬ ЦЕ)
# ==========================================

IMAGE_PATH = 'map.jpg'  # Шлях до вашого файлу
GEOJSON_FILE = 'poltava_regions.geojson' # Файл для збереження/завантаження

# 1. Реальні координати (Порядок: Полтава, Пирятин, Гадяч, Кременчук, Прилуки)
real_coords = np.array([
    [49.5883, 34.5514], 
    [50.2395, 32.5071], 
    [50.3678, 33.9797], 
    [49.0658, 33.4100], 
    [50.5885, 32.3876]
])

# 2. ВАШІ ПІКСЕЛЬНІ КООРДИНАТИ (X, Y)
# Впишіть сюди дані, які ви отримали!
pixel_coords = np.array([
    [3351, 2787], # Полтава
    [1965, 2120], # Пирятин
    [3048, 1960], # Гадяч
    [2590, 3254], # Кременчук
    [1881, 1769]  # Прилуки
])

# ==========================================
# ЛОГІКА
# ==========================================

class MapDigitizer:
    def __init__(self, img_path, pixels, coords):
        self.img = Image.open(img_path)
        self.pixels = pixels
        self.coords = coords
        
        # Обчислюємо матриці трансформації
        self.M_px_to_geo = self._get_transform(self.pixels, self.coords)
        self.M_geo_to_px = self._get_transform(self.coords, self.pixels)
        
        # Стан
        self.polygons = [] # Список завершених полігонів
        self.current_poly = [] # Поточний полігон (список точок)
        
        self._setup_plot()
        self.load_existing()

    def _get_transform(self, src, dst):
        """Обчислює афінну матрицю методом найменших квадратів"""
        # src_pad = [[x, y, 1], ...]
        src_pad = np.hstack([src, np.ones((src.shape[0], 1))])
        # M = (3, 2)
        M, _, _, _ = np.linalg.lstsq(src_pad, dst, rcond=None)
        return M

    def transform_points(self, points, matrix):
        """Перетворює масив точок за допомогою матриці"""
        pts = np.array(points)
        if len(pts) == 0: return []
        pad = np.hstack([pts, np.ones((pts.shape[0], 1))])
        return pad @ matrix

    def _setup_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        self.ax.imshow(self.img)
        self.ax.set_title("L-Click: Add Point | Click Start: Close Poly | 'd': Delete Point | 'q': Save & Quit")
        
        # Події
        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_key = self.fig.canvas.mpl_connect('key_press_event', self.onkey)
        
        self.poly_patches = []
        self.current_line, = self.ax.plot([], [], 'r-o', linewidth=2, markersize=4)

    def redraw(self):
        # Видаляємо старі патчі
        for p in self.poly_patches:
            p.remove()
        self.poly_patches = []

        # Малюємо завершені полігони
        for poly in self.polygons:
            patch = MplPolygon(poly, closed=True, facecolor='blue', edgecolor='yellow', alpha=0.3)
            self.ax.add_patch(patch)
            self.poly_patches.append(patch)

        # Малюємо поточний (незавершений)
        if self.current_poly:
            xs, ys = zip(*self.current_poly)
            self.current_line.set_data(xs, ys)
        else:
            self.current_line.set_data([], [])

        self.fig.canvas.draw()

    def onclick(self, event):
        if event.xdata is None or event.ydata is None: return
        # Тільки лівий клік
        if event.button != 1: return

        click_xy = (event.xdata, event.ydata)

        # Перевірка на закриття полігону (клік поруч з першою точкою)
        if len(self.current_poly) > 2:
            start_x, start_y = self.current_poly[0]
            dist = np.sqrt((click_xy[0] - start_x)**2 + (click_xy[1] - start_y)**2)
            
            # Допуск в пікселях (наприклад, 30 пікселів)
            if dist < 50: 
                print("Полігон замкнено!")
                self.polygons.append(self.current_poly)
                self.current_poly = []
                self.redraw()
                return

        self.current_poly.append(click_xy)
        self.redraw()

    def onkey(self, event):
        if event.key in ['d', 'delete', 'backspace']:
            if self.current_poly:
                self.current_poly.pop()
                self.redraw()
                print("Точка видалена")
            elif self.polygons:
                print("Видалення останнього завершеного полігону... (натисніть ще раз, якщо впевнені, тут поки що просто лог)")
                # Можна розкоментувати, якщо хочете видаляти цілі полігони
                # self.polygons.pop()
                # self.redraw()
        
        elif event.key == 'q':
            self.save_geojson()
            plt.close()

    def save_geojson(self):
        features = []
        for poly_px in self.polygons:
            # Конвертуємо пікселі -> Geo
            geo_points = self.transform_points(poly_px, self.M_px_to_geo)
            
            # GeoJSON вимагає [Lon, Lat], а у нас [Lat, Lon]
            # Тому міняємо колонки місцями
            geo_points_lonlat = geo_points[:, [1, 0]]
            
            # GeoJSON полігон має замикатися (перша точка == остання)
            coords = geo_points_lonlat.tolist()
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            features.append({
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            })

        data = {"type": "FeatureCollection", "features": features}
        
        with open(GEOJSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Дані збережено у {GEOJSON_FILE}")

    def load_existing(self):
        if not os.path.exists(GEOJSON_FILE):
            return
        
        print(f"Завантаження існуючого файлу: {GEOJSON_FILE}")
        with open(GEOJSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for feature in data.get('features', []):
            geom = feature.get('geometry', {})
            if geom.get('type') == 'Polygon':
                # GeoJSON це Lon, Lat
                geo_coords_lonlat = np.array(geom['coordinates'][0])
                # Нам треба Lat, Lon
                geo_coords_latlon = geo_coords_lonlat[:, [1, 0]]
                
                # Трансформуємо Geo -> Pixel
                px_coords = self.transform_points(geo_coords_latlon, self.M_geo_to_px)
                
                # Видаляємо останню точку дублікат (замикання) для редагування
                self.polygons.append(px_coords[:-1].tolist())
        
        self.redraw()

if __name__ == "__main__":
    # Перевірка
    if np.all(pixel_coords == 0):
        print("ПОМИЛКА: Будь ласка, відкрийте скрипт і впишіть pixel_coords (рядок 27)")
        sys.exit()

    app = MapDigitizer(IMAGE_PATH, pixel_coords, real_coords)
    plt.show()