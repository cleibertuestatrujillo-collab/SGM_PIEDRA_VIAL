import sys

# IMPORTANTE
from database.database import get_database

from PySide6.QtWidgets import QApplication
from ui.login import LoginWindow

# Crea la base de datos y las tablas (una sola conexión)
get_database()

app = QApplication(sys.argv)

ventana = LoginWindow()
ventana.show()

sys.exit(app.exec())