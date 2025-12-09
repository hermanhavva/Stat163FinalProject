import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import json
import os
import sys
from PIL import Image

# ==========================================
# сonfig
# ==========================================
IMAGE_PATH = './data/Poltava_governorate_1821.jpg' 
GEOJSON_FILE = 'poltava_regions.geojson'

# 1. Реальні координати
real_coords = np.array([
    [49.5883, 34.5514], # Полтава
    [50.2395, 32.5071], # Пирятин
    [50.3678, 33.9797], # Гадяч
    [49.0658, 33.4100], # Кременчук
    [50.5885, 32.3876]  # Прилуки
])

# 2. ПІКСЕЛЬНІ КООРДИНАТИ
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
        # Налаштування backend для кращої сумісності (спробуємо TkAgg, якщо є)
        try:
            import matplotlib
            matplotlib.use('TkAgg')
        except:
            pass # Використовуємо дефолтний, якщо TkAgg немає

        try:
            self.img = Image.open(img_path)
        except FileNotFoundError:
            print(f"Помилка: Файл {img_path} не знайдено.")
            sys.exit()

        self.pixels = pixels
        self.coords = coords
        
        self.M_px_to_geo = self._get_transform(self.pixels, self.coords)
        self.M_geo_to_px = self._get_transform(self.coords, self.pixels)
        
        self.polygons = []
        self.current_poly = []
        
        # Стан для панорамування (Drag)
        self.is_panning = False
        self.pan_start = None
        
        self._setup_plot()
        self.load_existing_geojson()

    def _get_transform(self, src, dst):
        src_pad = np.hstack([src, np.ones((src.shape[0], 1))])
        M, _, _, _ = np.linalg.lstsq(src_pad, dst, rcond=None)
        return M

    def transform_points(self, points, matrix):
        pts = np.array(points)
        if len(pts) == 0: return []
        pad = np.hstack([pts, np.ones((pts.shape[0], 1))])
        return pad @ matrix

    def _setup_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        self.ax.imshow(self.img)
        
        title_str = "CONTROLS:\n[Click]: Add Point | [Shift + Drag]: Move Map | [Scroll]: Zoom\n[Click Start]: Close Polygon | [D]: Delete Point | [Q]: Save"
        self.ax.set_title(title_str, fontsize=10)
        
        # Підключаємо всі події
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        
        self.poly_patches = []
        self.current_line, = self.ax.plot([], [], 'r-o', linewidth=2, markersize=4)

        try:
            mng = plt.get_current_fig_manager()
            mng.resize(*mng.window.maxsize())
        except:
            pass

    # --- ЛОГІКА ЗУМУ (SCROLL) ---
    def on_scroll(self, event):
        base_scale = 1.2
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        
        if xdata is None or ydata is None: return

        if event.button == 'up':
            scale_factor = 1/base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

        self.ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
        self.ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
        self.fig.canvas.draw()

    # --- ЛОГІКА КЛІКІВ ТА ПАНОРАМУВАННЯ (PAN) ---
    def on_press(self, event):
        if event.xdata is None or event.ydata is None: return
        if event.button != 1: return  # Тільки ліва кнопка

        # Якщо натиснуто SHIFT -> Починаємо рухати карту (Pan)
        if event.key == 'shift':
            self.is_panning = True
            self.pan_start = (event.xdata, event.ydata)
            # Міняємо курсор (візуально не зміниться в mpl, але логічно ми в режимі Drag)
            return

        # Якщо SHIFT НЕ натиснуто -> Ставимо точку
        self.add_point(event.xdata, event.ydata)

    def on_move(self, event):
        # Логіка руху карти (Pan)
        if self.is_panning and event.xdata is not None and event.ydata is not None:
            # Обчислюємо зсув
            dx = event.xdata - self.pan_start[0]
            dy = event.ydata - self.pan_start[1]
            
            # Зсуваємо межі
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            
            # Віднімаємо dx/dy, щоб карта рухалася за мишкою
            self.ax.set_xlim(cur_xlim - dx)
            self.ax.set_ylim(cur_ylim - dy)
            self.fig.canvas.draw()

    def on_release(self, event):
        if event.button == 1:
            self.is_panning = False
            self.pan_start = None

    def add_point(self, x, y):
        click_xy = (x, y)
        print(f"Click at: {int(x)}, {int(y)}") # Debug

        # Перевірка на замикання полігону
        if len(self.current_poly) > 2:
            start_x, start_y = self.current_poly[0]
            # Допуск збільшено для зручності при зумі
            dist = np.sqrt((click_xy[0] - start_x)**2 + (click_xy[1] - start_y)**2)
            
            # Розрахунок допуску відносно поточного масштабу (щоб працювало і при зумі)
            xlim = self.ax.get_xlim()
            scale_width = xlim[1] - xlim[0]
            tolerance = scale_width * 0.02 # 2% від ширини екрану
            
            if dist < tolerance: 
                print("Полігон замкнено!")
                self.polygons.append(self.current_poly)
                self.current_poly = []
                self.redraw()
                return

        self.current_poly.append(click_xy)
        self.redraw()

    def redraw(self):
        for p in self.poly_patches:
            p.remove()
        self.poly_patches = []

        for poly in self.polygons:
            patch = MplPolygon(poly, closed=True, facecolor='blue', edgecolor='yellow', alpha=0.3)
            self.ax.add_patch(patch)
            self.poly_patches.append(patch)

        if self.current_poly:
            xs, ys = zip(*self.current_poly)
            self.current_line.set_data(xs, ys)
        else:
            self.current_line.set_data([], [])

        self.fig.canvas.draw()

    def on_key(self, event):
        if event.key in ['d', 'delete', 'backspace']:
            if self.current_poly:
                self.current_poly.pop()
                self.redraw()
                print("Точка видалена")
            elif self.polygons:
                print("Скасовано останній полігон")
                self.current_poly = self.polygons.pop() # Повертаємо точки для редагування
                self.redraw()
        
        elif event.key == 'q':
            self.save_geojson()
            plt.close()

    def save_geojson(self):
        features = []
        for poly_px in self.polygons:
            geo_points = self.transform_points(poly_px, self.M_px_to_geo)
            geo_points_lonlat = geo_points[:, [1, 0]]
            coords = geo_points_lonlat.tolist()
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            features.append({
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            })

        data = {"type": "FeatureCollection", "features": features}
        
        with open(GEOJSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"ФАЙЛ ЗБЕРЕЖЕНО: {os.path.abspath(GEOJSON_FILE)}")

    def load_existing_geojson(self):
        if not os.path.exists(GEOJSON_FILE): return
        print(f"Завантаження: {GEOJSON_FILE}")
        try:
            with open(GEOJSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for feature in data.get('features', []):
                geom = feature.get('geometry', {})
                if geom.get('type') == 'Polygon':
                    geo_coords_lonlat = np.array(geom['coordinates'][0])
                    geo_coords_latlon = geo_coords_lonlat[:, [1, 0]]
                    px_coords = self.transform_points(geo_coords_latlon, self.M_geo_to_px)
                    self.polygons.append(px_coords[:-1].tolist())
            self.redraw()
        except Exception as e:
            print(f"Помилка завантаження файлу: {e}")

if __name__ == "__main__":
    if np.all(pixel_coords == 0):
        print("ПОМИЛКА: Заповніть pixel_coords!")
        sys.exit()

    app = MapDigitizer(IMAGE_PATH, pixel_coords, real_coords)
    plt.show()