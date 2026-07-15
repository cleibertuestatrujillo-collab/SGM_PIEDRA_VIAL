import sys

# IMPORTANTE
from database.database import Database

from PySide6.QtWidgets import QApplication
from ui.login import LoginWindow

# Crea la base de datos y las tablas
Database()

app = QApplication(sys.argv)

ventana = LoginWindow()
ventana.show()

sys.exit(app.exec())