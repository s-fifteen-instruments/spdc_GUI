# This program is a Graphical User Interface (GUI) for S-Fifteen Instruments'
# SPDC Drivers.
# Copyright (C) 2025

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#
# See bottom of file for a brief history of version updates.
#


import sys
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
    )
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import (
        pyqtSignal,
        pyqtSlot,
        QObject,
        QSize,
        QThread,
        QTimer
        )
from datetime import datetime
import time
from types import NoneType

from spdc_driver_trim import SPDCDriver
from serial_connection import search_for_serial_devices
from serial import SerialTimeoutException

"""[summary]
    This is the GUI for the SPDC Driver.
    It is used to view, set and control the device.

    Usage:

"""


Global_Style = """QPushButton
                {font-size: 20px }
                QDoubleSpinBox
                {font-size: 20px }
                """

DEVICE_IDENTIFIER = "SPDC"
digit_font_size = 41

class UpdateGUI(QObject):
    # Worker Signals

    thread_finished = pyqtSignal('PyQt_PyObject')
    #permission_error = pyqtSignal('PyQt_PyObject')
    # Data contains, start time, now time, device info, dev_mode,
    data_is_logged = pyqtSignal(float, float, dict, str)
    def __init__(self):
        super(UpdateGUI, self).__init__()
        self.active_flag = False
        self.unblocked = True
        self.runtime = 0

    # Connected to MainWindow enableDev.
    @pyqtSlot(object, str)
    def run(self,dev_handle: object, dev_mode: str):
        data = {}
        self.active_flag = True
        start = time.time()
        while self.active_flag == True:
            time.sleep(2)
            olddata = data
            data = self.get_data(dev_handle, dev_mode)
            if isinstance(data,NoneType):
                data = olddata
            now = time.time()
            self.data_is_logged.emit(start,now,data, dev_mode)
            if self.active_flag == False:
                break
        print('Terminating update')

    def get_data(self, dev_handle, dev_mode):
        """Read data from device
        """
        try:
            while self.unblocked:
                self.unblocked = False
                l_current = dev_handle.laser_current
                p_temp = dev_handle.peltier_temp
                p_voltage = dev_handle.peltier_voltage
                p_constp = dev_handle.pconstp
                p_consti = dev_handle.pconsti
                power = dev_handle.power
                status = dev_handle.status
                self.unblocked = True
                return {'lcurrent' : l_current,
                    'ptemp'    : p_temp,
                    'pvolt'    : p_voltage,
                    'pconstp'  : p_constp,
                    'pconsti'  : p_consti,
                    'power'    : power,
                    'status'   : status,
                    }
        except SerialTimeoutException:
            pass


class MainWindow(QMainWindow):
    """[summary]
    Main window class containing the main window and its associated methods. 
    Args:
        QMainWindow (QObject): See qt documentation for more info.
    """

    # Signal for updating GUI. device_handle and dev_mode passed
    update_requested = pyqtSignal(object, str)

    def __init__(self, *args, **kwargs):
        """[summary]
        Function to initialise the Main Window, which will hold all the subsequent widgets to be created.
        """
        super(MainWindow, self).__init__(*args, **kwargs)

        self._spdc_dev = None  # spdc device object
        self._dev_path = '' # Device path, eg. 'COM4', '/dev/ttyACM1'
        self._open_ports = []
        self.digit_font_size = digit_font_size
        self._dev_selected = False
        self.dev_list = []

        self.initUI() # UI is initialised afer the class variables are defined

        #self._dev_path_prev = self.devCombobox.currentText()
        #self._dev_mode_prev = self.modesCombobox.currentText()
        #self._level_prev = self.levelsComboBox.currentText()
        #self.integration_time_prev = self.integration_time
        #self.plotSamples_prev = self.plotSamples
        #self._ch_start_prev = self._ch_start
        #self._ch_stop_prev = self._ch_stop
        #self.offset_prev = self.offset
        #self.bin_width_prev = self.bin_width
        #self._runtime_prev = self._runtime

        #self._plot_tab = self.tabs.currentIndex()  # Counts graph = 0, Coincidences graph = 1
        #self.idx = min(len(self.y1), self.plotSamples)  # Index for plotting

    def initUI(self):
        """[summary]
        Contains all the UI elements and associated functionalities.
        """
        defaultFont = QFont("Helvetica", 20)

        #---------Buttons---------#

        self.powerButton = QPushButton("Power",self)
        self.powerButton.clicked.connect(self.toggle_power)
        self.powerButton.setStyleSheet("background-color: grey")
        self.powerButton.setEnabled(False)

        self.laserButton = QPushButton("Laser", self)
        self.laserButton.clicked.connect(self.toggle_laser)
        self.laserButton.setStyleSheet("background-color: grey")
        self.laserButton.setEnabled(False)

        # setAutoExclusive method is used to toggle the radio buttons independently.

        #---------Buttons---------#


        #---------Labels---------#
        self.deviceLabel = QLabel("Device:", self)
        self.currentSetLabel = QLabel("Laser Set Current:", self)
        self.currentActLabel = QLabel("Laser Actual Current:", self)
        self.currentAct = QLabel("", self)
        self.current1UnitLabel = QLabel("mA", self)
        self.current2UnitLabel = QLabel("mA", self)
        self.tempUnitLabel = QLabel(f"\N{DEGREE SIGN}C", self)
        self.temp2UnitLabel = QLabel(f"\N{DEGREE SIGN}C", self)
        self.lsettempLabel = QLabel("Laser Set Temperature:", self)
        self.lacttempLabel = QLabel("Laser Actual Temperature:", self)
        self.ltempLabel = QLabel("", self)
        self.pvoltLabel = QLabel("Peltier Voltage:", self)
        self.pvolt = QLabel("", self)
        self.pvoltUnitLabel = QLabel("V", self)

        #---------Labels---------#


        #---------Interactive Fields---------#
        try:
            # Do twice cause ATMEL chips may ignore query when first plugged in
            self.dev_list = search_for_serial_devices(
                    DEVICE_IDENTIFIER)
            self.dev_list = search_for_serial_devices(
                    DEVICE_IDENTIFIER)
        except:
            pass

        self.devCombobox = QComboBox(self)
        self.devCombobox.addItem('Select your device')
        self.devCombobox.addItems(self.dev_list)
        self.devCombobox.currentTextChanged.connect(self.selectDevice)

        self.lcurr = QDoubleSpinBox(self)
        self.lcurr.setRange(0, 50)  # Max Current depend on device limit.
        self.lcurr.setValue(0) #
        self.lcurr.valueChanged.connect(self.update_lcurr)
        self.lcurr.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.lcurr.setEnabled(False)

        self.lsettemp = QDoubleSpinBox(self)
        self.lsettemp.setRange(19, 30)
        self.lsettemp.setValue(20.5) # Default 
        self.lsettemp.setKeyboardTracking(False)
        self.lsettemp.valueChanged.connect(self.update_ltemp)
        self.lsettemp.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.lsettemp.setEnabled(False)

        #self.offsetSpinbox = QDoubleSpinBox(self)
        #self.offsetSpinbox.setRange(-10, 65535)
        #self.offsetSpinbox.setValue(35)
        #self.offsetSpinbox.setKeyboardTracking(False)
        #self.offsetSpinbox.valueChanged.connect(self.empty_func)
        #self.offsetSpinbox.setEnabled(False)

        #---------Interactive Fields---------#


        #---------PLOTS---------#
        # Initiating plot data variables
        #---------PLOTS---------#

        # Timer
        self.timer = QTimer()

        #---------Main Window---------#
        self.setWindowTitle("SPDC Driver")
        self.move(0, 0)
        #---------Main Window---------#


        #---------Tabs---------#
        #---------Tabs---------#

        #--------Layout--------#
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.grid.addWidget(self.deviceLabel,0,0)
        self.grid.addWidget(self.devCombobox,0,1)
        self.grid.addWidget(self.powerButton,1,0)
        self.grid.addWidget(self.laserButton,2,0)
        self.grid.addWidget(self.currentSetLabel,3,0)
        self.grid.addWidget(self.lcurr,3,1)
        self.grid.addWidget(self.current1UnitLabel,3,2)
        self.grid.addWidget(self.currentActLabel,4,0)
        self.grid.addWidget(self.currentAct,4,1)
        self.grid.addWidget(self.current2UnitLabel,4,2)
        self.grid.addWidget(self.lsettempLabel,5,0)
        self.grid.addWidget(self.lsettemp,5,1)
        self.grid.addWidget(self.tempUnitLabel,5,2)
        self.grid.addWidget(self.lacttempLabel,6,0)
        self.grid.addWidget(self.ltempLabel,6,1)
        self.grid.addWidget(self.temp2UnitLabel,6,2)
        self.grid.addWidget(self.pvoltLabel,7,0)
        self.grid.addWidget(self.pvolt,7,1)
        self.grid.addWidget(self.pvoltUnitLabel,7,2)

        #Main Widget (on which the grid is to be implanted)
        self.mainwidget = QWidget()
        self.mainwidget.layout = self.grid
        self.mainwidget.setLayout(self.mainwidget.layout)
        self.mainwidget.setFont(defaultFont)
        self.setCentralWidget(self.mainwidget)
        #--------Layout--------#

    def toggle_power(self):
        """
        """
        read_out = False
        while not read_out:
            print("Toggle power function called")
            if self.logger.unblocked:
                status = self._spdc_dev.status
                other_power = (status&256)>>8
                if other_power == 0:
                    self._spdc_dev.peltier_loop_on()
                    if self._dev_mode == 'EPPS':
                        self._spdc_dev.heater_loop_on()
                    print("Power on")
                else:
                    self._spdc_dev.peltier_loop_off()
                    self._spdc_dev.heater_loop_off()
                    print("Power off")
                read_out = True

    def toggle_laser(self):
        """
        """
        read_out = False
        while not read_out:
            print("Toggle laser function called")
            if self.logger.unblocked:
                #self.logger.unblocked = False
                status = self._spdc_dev.status
                laser_power = (status&512)>>9
                laser_on = (status&4)>>2
                if laser_on == 0 and laser_power == 0:
                    curr = self.lcurr.value()
                    self._spdc_dev.laser_off()
                    self._spdc_dev.laser_on(curr)
                    time.sleep(0.02)
                    print("Laser on")
                elif laser_power ==1 and laser_on == 1:
                    curr = self._spdc_dev.laser_current
                    self._spdc_dev.laser_off()
                    self._spdc_dev.old_laser_current = curr
                    time.sleep(0.02)
                    print("Laser off")
                #self.logger.unblocked = True
                read_out = True

    @pyqtSlot(float)
    def update_ltemp(self, curr_value: float):
        pass


    @pyqtSlot(float)
    def update_lcurr(self, curr_value: float):
        """ Empty function
        """
        print("update_lcurr called")
        self._spdc_dev.laser_current = curr_value

    # Connected to devComboBox.currentTextChanged
    @pyqtSlot(str)
    def selectDevice(self, devPath: str):
        if devPath == 'Select your device':
            if self._dev_selected:
                self.disableDevOptions()
                self._spdc_dev.close()
            return
        #self.StrongResetInternalVariables()
        print('Creating SPDC object.')
        self._spdc_dev = SPDCDriver(devPath)
        self._dev_path = devPath
        check = self._spdc_dev._com.portstr
        print(f'Device connected at {check}')
        self.set_devmode()
        self.enableDevOptions()
        self._dev_selected = True

    def set_devmode(self):
        CPPS_List = ['SPDC driver, svn-05',
       'S-15 Instruments SPDC source driver, firmware svn-5. Serial: SPDCSDR-10',
       'S-15 Instruments SPDC source driver, firmware svn-7. Serial: SPDCSDR-99',
                ]
        idn = self._spdc_dev.identity
        if idn in CPPS_List:
            self._dev_mode = 'CPPS'
        else:
            self._dev_mode = 'EPPS'
        print(f'Device is a {self._dev_mode}')
        return

    def StrongResetInternalVariables(self):
        #self.deleteWorkerAndThread()
        try:
            self._spdc_dev._com.close()
        except AttributeError:
            print('SPDC object not yet created.')
        finally:
            self._spdc_dev = None  # tdc1 device object
            self._dev_mode = ''
            self._dev_path = '' # Device path, eg. 'COM4'

    def enableDevOptions(self):
        self.powerButton.setEnabled(True)
        if self._spdc_dev.power&1 == 1:
            self.powerButton.setStyleSheet("background-color: green")
        else:
            self.powerButton.setStyleSheet("background-color: red")
        self.laserButton.setEnabled(True)
        if self._spdc_dev.power&2 == 2 and self._spdc_dev.status&4 == 4:
            self.laserButton.setStyleSheet("background-color: green")
            self.lcurr.setEnabled(True)
        else:
            self.laserButton.setStyleSheet("background-color: red")
            self.lcurr.setEnabled(False)
        self.lcurr.setRange(0,self._spdc_dev.laser_current_limit)
        self.lcurr.setValue(self._spdc_dev.laser_current)
        self.lsettemp.setValue(20.0) # Default 
        self.lsettemp.setEnabled(True)
        #self.samplesSpinbox.setEnabled(True)
        #self.liveStart_Button.setEnabled(True)
        #self.selectLogfile_Button.setEnabled(True)
        #self.runtimeSpinbox.setEnabled(True)
        self.start_gui_update()

    def start_gui_update(self):
        """
        Start processes needed to update the GUI via QThread.
        """
        self.logger = UpdateGUI()
        self.logger_thread = QThread(self)
        # Assign worker to the thread and start the thread
        self.logger.moveToThread(self.logger_thread)
        self.logger_thread.start()

        # Connect signals and slots AFTER moving the object to the thread
        self.update_requested.connect(self.logger.run)
        self.logger.data_is_logged.connect(self.update_from_thread)
        self.logger.thread_finished.connect(self.closethreads_ports_timers)
        #self.logger.permission_error.connect(self.logfile_permission_error_reset)
        self.update_requested.emit(self._spdc_dev,self._dev_mode)

    def disableDevOptions(self):
        try:
            self.logger.active_flag = False
            time.sleep(1.0)
        except:
            pass
        self.powerButton.setEnabled(False)
        self.laserButton.setEnabled(False)
        self.lcurr.setEnabled(False)
        #self.integrationSpinBox.setEnabled(False)
        #self.samplesSpinbox.setEnabled(False)
        #self.liveStart_Button.setEnabled(False)
        #self.selectLogfile_Button.setEnabled(False)

    # Updating data
    # Connected to data_is_logged signal
    pyqtSlot(float, float, dict, str)
    def update_from_thread(
            self, start: float,
            now: float,
            data: dict,
            dev_mode: str,
            ):
        next_time = now-start
        self.ltempLabel.setText(str(data['ptemp']))
        self.currentAct.setText(str(data['lcurrent']))
        self.pvolt.setText(str(data['pvolt']))
        power = int(data['power'])
        if power&1 == 1:
            self.powerButton.setStyleSheet("background-color: green")
        else:
            self.powerButton.setStyleSheet("background-color: red")
        status = int(data['status'])
        if power&2 == 2 and status&4 == 4:
            self.laserButton.setStyleSheet("background-color: green")
            self.lcurr.setEnabled(True)
        else:
            self.laserButton.setStyleSheet("background-color: red")
            self.lcurr.setEnabled(False)
        if dev_mode == 'EPPS':
            # Extra heater info for EPPS
            pass
            #self.htempLabel.setText(str(data['hvolt']))

    @pyqtSlot('PyQt_PyObject')
    def closethreads_ports_timers(self, dev):
        pass

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setStyleSheet(Global_Style)
    win.show()
    app.aboutToQuit.connect(win.destroy)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


