import pyqtgraph as pg
from PyQt6.QtCore import Qt
from .settings import STATS

def setup_graphs(gui):
    # --- Graph ---
    gui.graph = pg.PlotWidget(title="📈 Stats Over Time")
    gui.graph.addLegend()
    gui.graph.showGrid(x=True, y=True)
    gui.graph_curves = {}
    for i, stat in enumerate(STATS):
        pen = pg.mkPen(pg.intColor(i, hues=len(STATS)), width=2)
        gui.graph_curves[stat] = gui.graph.plot(pen=pen, name=stat.capitalize())
    gui.main_layout.addWidget(gui.graph)

    gui.gap_graph = pg.PlotWidget(title="📊 Gap to Ideal Over Time")
    gui.gap_graph.addLegend()
    gui.gap_graph.showGrid(x=True, y=True)
    gui.gap_curves = {}
    for i, stat in enumerate(STATS):
        pen = pg.mkPen(pg.intColor(i, hues=len(STATS)), width=2, style=Qt.PenStyle.DashLine)
        gui.gap_curves[stat] = gui.gap_graph.plot(pen=pen, name=stat.capitalize())
    gui.main_layout.addWidget(gui.gap_graph)

def update_graph(gui):
    x = list(range(1, len(gui.history)+1))
    for s in STATS:
        y = [h[s] for h in gui.history]
        gui.graph_curves[s].setData(x, y)
        gap_values = [gui.ideal_stats[s] - val for val in y]
        gui.gap_curves[s].setData(x, gap_values)
