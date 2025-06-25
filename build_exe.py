import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',  # основной файл вашего проекта
    '--onefile',
    '--windowed',
    '--name=ver1.0.B5',
    '--add-data=office.db;.',  # база данных (для Windows, для Linux замените ; на :)
    '--hidden-import=openpyxl',
    '--hidden-import=xlsxwriter',
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.backends.backend_qtagg',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets'
])
