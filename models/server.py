from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.UserParam import UserSettableParameter

from model import Triangles



server = ModularServer(
    Triangles, [canvas_element, happy_element, happy_chart], "Triangles", model_params
)

