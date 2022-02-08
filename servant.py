import json

# import qdarkstyle
import PyQtJsonModel
import qtmHelper
import requests
import qtmHelper
import logging
import pandas as pd

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QJsonDocument,
    QJsonParseError,
    QMutex,
    QAbstractTableModel  
)
from PySide6.QtWidgets import QApplication, QTreeView, QWidget, QHBoxLayout

logging.basicConfig(format="%(message)s", level=logging.INFO)
gQtmData = qtmHelper.qtmData()

mutex = QMutex()


class DataFrameModel(QAbstractTableModel):
    DtypeRole = Qt.UserRole + 1000
    ValueRole = Qt.UserRole + 1001

    def __init__(self, df=pd.DataFrame(), parent=None):
        super(DataFrameModel, self).__init__(parent)
        self._dataframe = df

    def setDataFrame(self, dataframe):
        self.beginResetModel()
        self._dataframe = dataframe.copy()
        self.endResetModel()

    def dataFrame(self):
        return self._dataframe

    dataFrame = QtCore.Property(pd.DataFrame, fget=dataFrame, fset=setDataFrame)

    @QtCore.Slot(int, QtCore.Qt.Orientation, result=str)
    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.DisplayRole,
    ):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._dataframe.columns[section]
            else:
                return str(self._dataframe.index[section])
        return None

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._dataframe.index)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return self._dataframe.columns.size

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (
            0 <= index.row() < self.rowCount()
            and 0 <= index.column() < self.columnCount()
        ):
            return None
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype

        val = self._dataframe.iloc[row][col]
        if role == QtCore.Qt.DisplayRole:
            return str(val)
        elif role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return None

    def roleNames(self):
        roles = {
            QtCore.Qt.DisplayRole: b"display",
            DataFrameModel.DtypeRole: b"dtype",
            DataFrameModel.ValueRole: b"value",
        }
        return roles


class dataWorker(QtCore.QObject):
    finished = QtCore.Signal()
    updatedBalance = QtCore.Signal()

    def loadQTMData(self, fileName):
        logging.info("Started loading QTM data")
        global gQtmData
        mutex.lock()
        gQtmData.loadFromFile(fileName=fileName)
        mutex.unlock()
        self.finished.emit()


# class dataMarkersListModel(QtCore.QAbstractListModel):
#     def __init__(self, markerList=None):
#         super(dataMarkersListModel, self).__init__
#         self.markerList = todos or []
#     def data(self, index, role):
#         if role == Qt.DisplayRole:
#             # See below for the data structure.
#             status, text = self.todos[index.row()]
#             # Return the todo text only.
#             return text

#     def rowCount(self, index):
#         return len(self.todos)
gMarkerDataModel = DataFrameModel()


class dataViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.markerListView = QtWidgets.QListView()
        self.markerListView.setMaximumSize(300, 2000)
        self.layout.addWidget(self.markerListView)
        self.markersListModel = QtCore.QStringListModel()
        self.markersListModel.setStringList(gQtmData.data["Markers"].keys())
        self.markerListView.setModel(self.markersListModel)
        #        self.markerListView.setSelectionModel(QtGui.QItemView.ExtendedSelectio)

        self.markerDataView = QtWidgets.QTableView()
        self.markerDataView.setModel(gMarkerDataModel)
        self.layout.addWidget(self.markerDataView)
        self.z = self.markerListView.selectionModel()
        self.z.currentChanged.connect(self.on_row_changed)

    def update(self):
        self.markersListModel.setStringList(gQtmData.data["Markers"].keys())
        gMarkerDataModel = DataFrameModel(gQtmData.data["Markers"]["ZSJ_RAnkleOut"])
        self.markerDataView.setModel(gMarkerDataModel)

    def on_row_changed(self, current, previous):
        print("Row %d selected" % current.row())
        print(self.markersListModel.data(current, QtCore.Qt.ItemDataRole.DisplayRole))
        gMarkerDataModel = DataFrameModel(
            gQtmData.data["Markers"][
                self.markersListModel.data(current, QtCore.Qt.ItemDataRole.DisplayRole)
            ]
        )
        self.markerDataView.setModel(gMarkerDataModel)


class settingsWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.btnLoad = QtWidgets.QPushButton("Load from QTM")
        self.btnSave = QtWidgets.QPushButton("Save to QTM")
        self.settingsView = QtWidgets.QTreeView()
        self.layout.addWidget(self.settingsView)
        self.layout.addWidget(self.btnLoad)
        self.layout.addWidget(self.btnSave)
        self.settingsModel = PyQtJsonModel.QJsonModel()
        self.settingsView.setModel(self.settingsModel)
        self.btnLoad.clicked.connect(self.loadSettings)
        self.btnSave.clicked.connect(self.saveSettings)

    @QtCore.Slot()
    def loadSettings(self, s):
        reqString = "http://10.211.55.3:7979/api/experimental/settings/"
        response = requests.get(reqString)
        document = response.json()
        self.jsonFile = response.json()
        self.settingsModel.clear()
        self.settingsModel.update_data(document)

    def saveSettings(self, s):
        reqString = "http://localhost:7979/api/experimental/settings"
        settingsJson = self.settingsModel.json()

        print(self.jsonFile)
        response = requests.post(reqString, json=settingsJson)
        print(response)
        print(response.content)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QServant")
        self.qtmData = qtmHelper.qtmData()
        # exit option for the menu bar File menu
        #self.exit = QtWidgets.QAction("Exit", self)
        # message for the status bar if mouse is over Exit
#        self.exit.setStatusTip("Exit program")
        # newer connect style (PySide/PyQT 4.5 and higher)
#        self.exit.triggered.connect(app.quit)

        # create the menu bar
        menubar = self.menuBar()
        file = menubar.addMenu("&File")
        loadData = file.addAction("&Load data")
        loadData.triggered.connect(self.load3DData)
        saveData = file.addAction("&Save data")
#        close = file.addAction(self.exit)

        # create the status bar
        self.statusBar()

        # QWidget or its instance needed for box layout
        self.widget = settingsWidget()
        self.markersListWidget = dataViewWidget()
        # make it the central widget of QMainWindow
        self.setCentralWidget(self.widget)

    # @QtCore.Slot()
    def load3DData(self):
        gQtmData.loadFromFile("data.pkl")
        self.setCentralWidget(self.markersListWidget)
        self.markersListWidget.update()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.resize(800, 600)

    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside2'))
    mainWindow.show()

    app.exec_()
