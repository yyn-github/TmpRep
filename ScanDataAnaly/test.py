from PyQt5 import QtCore, QtGui, QtWidgets, QtChart
import math
import numpy as np
import pandas as pd


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.step = 0.1
        self._chart_view = QtChart.QChartView()
        self.scrollbar = QtWidgets.QScrollBar(
            QtCore.Qt.Horizontal,
            sliderMoved=self.onAxisSliderMoved,
            pageStep=self.step * 100,
        )
        self.slider = QtWidgets.QSlider(
            QtCore.Qt.Horizontal, sliderMoved=self.onZoomSliderMoved
        )

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        lay = QtWidgets.QVBoxLayout(central_widget)
        for w in (self._chart_view, self.scrollbar, self.slider):
            lay.addWidget(w)

        self.resize(640, 480)

        self._chart = QtChart.QChart()

        self._candlestick_serie = QtChart.QCandlestickSeries()
        self._line_serie = QtChart.QLineSeries()

        tm = []
        df = pd.read_csv(
            "https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv"
        )
        name_of_columns = ("AAPL.Open", "AAPL.High", "AAPL.Low", "AAPL.Close", "mavg")

        for i, (o, h, l, c, v) in enumerate(
            zip(*(df[name] for name in name_of_columns))
        ):
            self._candlestick_serie.append(QtChart.QCandlestickSet(o, h, l, c))
            self._line_serie.append(QtCore.QPointF(i, v))
            tm.append(str(i))

        min_x, max_x = 0, i

        self._chart.addSeries(self._candlestick_serie)
        self._chart.addSeries(self._line_serie)
        self._chart.createDefaultAxes()
        self._chart.legend().hide()
        # self._chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self._chart.axisX(self._candlestick_serie).setCategories(tm)
        self._chart.axisX(self._candlestick_serie).setVisible(False)

        self._chart_view.setChart(self._chart)
        self.adjust_axes(100, 200)
        self.lims = np.array([min_x, max_x])

        self.onAxisSliderMoved(self.scrollbar.value())

    def adjust_axes(self, value_min, value_max):
        self._chart.axisX(self._candlestick_serie).setRange(
            str(value_min), str(value_max)
        )
        self._chart.axisX(self._line_serie).setRange(value_min, value_max)

    @QtCore.pyqtSlot(int)
    def onAxisSliderMoved(self, value):
        r = value / ((1 + self.step) * 100)
        l1 = self.lims[0] + r * np.diff(self.lims)
        l2 = l1 + np.diff(self.lims) * self.step
        self.adjust_axes(math.floor(l1), math.ceil(l2))

    @QtCore.pyqtSlot(int)
    def onZoomSliderMoved(self, value):
        print(value)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())