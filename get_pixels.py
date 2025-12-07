import matplotlib.pyplot as plt
from PIL import Image
import sys

# Вкажіть шлях до вашого файлу
image_path = './data/Poltava_governorate_1821.jpg' 

try:
    img = Image.open(image_path)
except FileNotFoundError:
    print(f"Помилка: Файл {image_path} не знайдено.")
    sys.exit()

# Створюємо фігуру більшого розміру
fig, ax = plt.subplots(figsize=(14, 10))
ax.imshow(img)
ax.set_title("Scrool to Zoom | Click to add point | Right Click to exit")

print("--- Інструкція ---")
print("1. SCROLL (Колесо/Трекпад): Наближати/Віддаляти.")
print("2. PAN (Затисніть ліву кнопку і тягніть): Переміщення картою (тільки якщо включений інструмент 'Pan' внизу, або спробуйте стрілки).")
print("   *Кращий варіант:* Використовуйте іконку 'Лупи' внизу для зуму, потім вимикайте її, щоб поставити точку.")
print("3. CLICK: Ліва кнопка — записати координати.")
print("------------------")

coords = []

# --- Логіка Зуму ---
def zoom_factory(ax, base_scale=1.1):
    def zoom_fun(event):
        # Отримуємо поточні межі
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        
        if xdata is None or ydata is None:
            return

        if event.button == 'up':
            # Deal with zoom in
            scale_factor = 1/base_scale
        elif event.button == 'down':
            # Deal with zoom out
            scale_factor = base_scale
        else:
            # Deal with something that should never happen
            scale_factor = 1

        # Нова ширина і висота
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
        ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
        ax.figure.canvas.draw()

    fig = ax.get_figure()
    fig.canvas.mpl_connect('scroll_event', zoom_fun)
    return zoom_fun

# Підключаємо зум до нашого вікна
zoom_factory(ax)

# --- Логіка Кліків ---
def onclick(event):
    # Ігноруємо кліки, якщо активовано режим зуму або переміщення в тулбарі Matplotlib
    if fig.canvas.toolbar.mode != "":
        return

    # Лівий клік (button 1) і координати існують
    if event.button == 1 and event.xdata is not None and event.ydata is not None:
        ix, iy = int(event.xdata), int(event.ydata)
        print(f"Пікселі: x={ix}, y={iy}  <-- Запишіть назву міста")
        coords.append((ix, iy))
        
        # Малюємо хрестик замість точки для кращої видимості
        ax.plot(ix, iy, 'rx', markersize=10, markeredgewidth=2)
        # Додаємо номер точки поруч
        ax.text(ix + 5, iy + 5, str(len(coords)), color='red', fontsize=12, fontweight='bold')
        
        fig.canvas.draw()

cid = fig.canvas.mpl_connect('button_press_event', onclick)

# Максимізуємо вікно (може залежати від бекенду macOS, але спробуємо)
try:
    mng = plt.get_current_fig_manager()
    # Команда для TkAgg/Qt, на macosx може не спрацювати, тому ми задали великий figsize вище
    mng.resize(*mng.window.maxsize())
except:
    pass

plt.show()