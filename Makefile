all:	gui

gui:	spdc_GUI.py spdc_gui.spec
			pyinstaller.exe --onefile --windowed -y -n "SPDC_GUI" spdc_GUI.py serial_connection.py spdc_driver_trim.py

