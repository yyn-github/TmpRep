'''
 # @ Author: Your name
 # @ Create Time: 2023-02-15 17:12:43
 # @ Modified by: Your name
 # @ Modified time: 2023-02-15 17:13:29
 # @ Description:
 '''


import time
import sys
import os
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QLabel, QTextEdit, QPushButton, QLineEdit, QVBoxLayout, QSystemTrayIcon, QMenu, QAction, QComboBox, QFileDialog, QScrollBar
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QScreen
from PyQt5 import QtGui, uic
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis, QAbstractAxis, QBarSeries, QBarSet
import configparser
import numpy as np
import pandas as pd

class SectionItem:
	flash_id = ''
	flash_name = ''
	cfg_index = 0

	def __init__(self, id , name, index):
		self.flash_id = id
		self.flash_name = name
		self.cfg_index = index

	def is_similar(self, str):
		if self.flash_id.find(str):
			return True
		
		if self.flash_name.find(str):
			return True

		return False

	def get_flash_id(self):
		return self.flash_id
	
	def get_index(self):
		return self.cfg_index

class Config:
	#config item
	section_list = [SectionItem]

	def LoadSetting(self):
		self.config = configparser.ConfigParser()
		self.config.read('flash.ini', encoding='utf-16')
		index:int = 0
		for section in self.config.sections():
			item = SectionItem(section, self.config[section]['Name'], index)
			self.section_list.append(item)
			index += 1

	def get_flash_id(self):
		return self.config.sections() 

	def search_flash_id(self, str: str, vec:list):
		for item in self.section_list:
			if item.is_similar(str):
				vec.append(item.get_flash_id())
			
	
	def get_plane_per_ce(self, id):
		return int(self.config[id]['PlaneOfBank']) * int(self.config[id]['BankOfChip'])

	def get_plane_per_bank(self, id):
		return int(self.config[id]['PlaneOfBank']) 

	def get_block_per_bank(self, id):
		return int(self.config[id]['PhysicBlockOfBank'])

	def get_block_per_plane(self, id):
		return int(self.get_block_per_bank(id) / self.get_plane_per_ce(id)) 

	def get_phyical_page(self, id):
		valid_page = int(self.config[id]['ValidPageOfBlock'])
		erase_page = int(self.config[id]['ErasePageOfBlock'])

		phy_page = self.get_fixed_page(erase_page) if valid_page > erase_page else self.get_fixed_page(valid_page)
		return int(phy_page)
	
	def get_fixed_page(self, page):
		for i in range(1,32):
			if 1 << i >= page:
				return 1 << i

class ScanData:
	data_list = list() 
	def init(self, ce:int, block_per_ce:int, page_per_block:int):
		self.ce_number = ce
		self.block_number = block_per_ce
		self.page_bumber = page_per_block
	
	def build_data(self, data):
		for ce in range(0, self.ce_number):
			for block in range(0, self.block_number):
				offset = (ce * self.block_number * self.page_bumber) + (block * self.page_bumber)
				self.data_list.append(data[offset: offset + self.page_bumber])
	
	def get_block_info(self, block):
		return self.data_list[block]

class CoreWnd(QDialog):
	scan_data = ScanData()
	flash_id = ''
	def __init__(self):
		super(QDialog, self).__init__()
		self.resize(650, 800)

	def set_config(self, config: Config):
		self.config = config
		self.init_control()

	def init_control(self):
		self.layout = QVBoxLayout()
		self.setLayout(self.layout)

		#set flash id comboBox
		self.id_lab = QLabel('FlashID', self)
		self.layout.addWidget(self.id_lab)
		self.id_cmbox = QComboBox(self)
		for id in self.config.get_flash_id():
			self.id_cmbox.addItem(id)
		self.layout.addWidget(self.id_cmbox)

		#set find id edit
		self.id_search_lab = QLabel('search', self)
		self.layout.addWidget(self.id_search_lab)
		self.id_search_edt = QLineEdit(self)
		self.layout.addWidget(self.id_search_edt)
		self.id_search_cmbox = QComboBox(self)
		self.id_search_cmbox.currentIndexChanged.connect(self.search_id_clicked)
		self.layout.addWidget(self.id_search_cmbox)
		self.id_search_but = QPushButton('search',self)
		self.id_search_but.clicked.connect(self.search_flash_id)
		self.layout.addWidget(self.id_search_but)

		#set ce number comboBox
		self.ce_lab = QLabel('CE', self)
		self.layout.addWidget(self.ce_lab)
		self.ce_cmbox = QComboBox(self)
		for i in range(0, 4):
			self.ce_cmbox.addItem(str(pow(2, i)))
		self.ce_number = 1
		self.ce_cmbox.setCurrentIndex(0)
		self.ce_cmbox.currentIndexChanged.connect(self.set_ce_number)
		self.layout.addWidget(self.ce_cmbox)

		#set lowinfo edt
		self.info_lab = QLabel('File',self)
		self.layout.addWidget(self.info_lab)
		self.info_edt = QLineEdit(self)
		self.info_edt.setText('C:/Porject/ScanDataAnaly/TlcScanInfo.sd')
		self.layout.addWidget(self.info_edt)
		self.info_but = QPushButton('...', self)
		self.info_but.clicked.connect(self.open_scan_file)
		self.layout.addWidget(self.info_but)
		# self.layout.addStretch()

		#set show mode of chart
		self.chart_mode_cmbox = QComboBox()
		self.chart_mode_cmbox.addItem('AvgEcc')
		self.chart_mode_cmbox.addItem('PageMask')
		self.chart_mode_cmbox.currentIndexChanged.connect(self.change_chart_mode)
		self.layout.addWidget(self.chart_mode_cmbox)

		#set start button
		self.start_but = QPushButton('Start', self)
		self.start_but.clicked.connect(self.start)
		self.layout.addWidget(self.start_but)

		#set chart
		self.chart = QChart()
		self.chart_view = QChartView(self.chart)
		# self.chart_view.setRenderHint(QPainter::QRender.Antialiasing)
		self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
		self.layout.addWidget(self.chart_view)

	def search_flash_id(self, str):
		result = list()
		self.config.search_flash_id(str, result)
		if len(result) != 0:
			for id in result:
				self.id_search_cmbox.addItem(id)

	def search_id_clicked(self, index):
		self.id_cmbox.setCurrentText( self.id_search_cmbox.currentText())

	def set_ce_number(self, num):
		self.ce_number = num

	def open_scan_file(self):
		file_dig = QFileDialog(self)
		self.file_path:str = file_dig.getOpenFileName()[0]
		self.info_edt.setText(self.file_path)


	def start(self):
		# id = self.id_cmbox.currentText()
		# self.scan_data.init(self.ce_number,self.config.get_block_per_bank(id),self.config.get_phyical_page(id))

		# #parse scan info
		# f = open(self.file_path, 'rb')
		# f.seek(0, os.SEEK_END)
		# len = f.tell()
		# data = f.read(len)
		# self.scan_data.build_data(data)

		# if self.chart_mode_cmbox.currentIndex() == 1:
		# 	self.show_avg_ecc_chart()
		# else:
		# 	self.show_page_mask_chart()

		self.show_page_mask_chart()
		# self.show_chart_demo()

	def show_avg_ecc_chart(self):
		pass

	def show_page_mask_chart(self):
		id = self.id_cmbox.currentText()
		total_block = self.config.get_block_per_bank(id) * self.ce_number
		total_plane = int(self.ce_number * self.config.get_plane_per_ce(id))

		self.x_axis = QValueAxis()
		self.x_axis.setRange(0, int(total_block / total_plane) - 1)
		self.x_axis.setTickCount(int(total_block / total_plane))
		self.x_axis.setLabelFormat('%d')
		self.chart_scroll = QScrollBar(Qt.Horizontal)
		self.chart_scroll.sliderMoved.connect(self.on_axis_moved)
		# self.chart_view.scrollBarWidgets(self.chart_scroll)
		self.layout.addWidget(self.chart_scroll)

		self.y_axis = QValueAxis()
		self.y_axis.setRange(0, 68)
		self.y_axis.setTickCount(1)
		self.y_axis.setLabelFormat('%d')

		self.chart.setAxisX(self.x_axis)
		self.chart.setAxisY(self.y_axis)

		self.planes_line_series = list()
		for plane in range(0, self.config.get_plane_per_ce(id) * self.ce_number):
			series_title = 'Plane(' + str(plane) + ')'
			series = QLineSeries()
			series.setName(series_title)
			self.planes_line_series.append(series)

		for block in range(0, total_block):
			ce = int(block / self.config.get_block_per_bank(id))
			plane = int(block % self.config.get_plane_per_ce(id)) + int(ce * self.config.get_plane_per_ce(id))
			block_offset = int(block / self.config.get_plane_per_ce(id))
			ecc_val = random.randint(0, 68)
			self.planes_line_series[plane].append(block_offset, ecc_val)
			print(plane, block_offset , ecc_val)
		
		for plane in range(0, self.config.get_plane_per_ce(id) * self.ce_number):
			self.chart.addSeries(self.planes_line_series[plane])
		
		# self.chart.axisX().setRange(0,20)

	def adjust_axis(self, min, max):
		for plane_series in self.planes_line_series:
			self.chart.axisX(self.plane_series).setRange(str(min),str(max))

	def on_axis_moved(self, value):
		self.adjust_axis()
        # r = value / ((1 + 0.1) * 100)
        # l1 = self.lims[0] + r * np.diff(self.lims)
        # l2 = l1 + np.diff(self.lims) * self.step
        # self.adjust_axes(math.floor(l1), math.ceil(l2))
	
	# def show_chart_demo(self):
	# 	self.x_axis = QValueAxis()
	# 	self.x_axis.setRange(0, 100)
	# 	self.y_axis = QValueAxis()
	# 	self.y_axis.setRange(0, 100)

	# 	self.bar_series = QBarSeries()
	# 	bar_set = QBarSet(str(i))
	# 	for block in
	# 	bar_set.append(random.randint(0,100))
	# 	self.bar_series.append(bar_set)

	# 	self.chart.addSeries(self.bar_series)


	def change_chart_mode(self, mode):
		if mode == 0:
			pass
		else:
			pass



if __name__ == "__main__":
	app = QApplication(sys.argv)

	#load setting
	config = Config()
	config.LoadSetting()

	#attach setting
	window = CoreWnd()
	window.set_config(config)

	#show window
	window.show()
	sys.exit(app.exec_())