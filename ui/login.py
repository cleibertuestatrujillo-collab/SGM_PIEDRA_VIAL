import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
)

from ui.dashboard import Dashboard


class LoginWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SGM Piedra Vial")
        self.setFixedSize(450, 350)

        self.db = Path(__file__).parent.parent / "database" / "sgm.db"

        self.setStyleSheet("""
        QWidget{
            background:#1E293B;
            color:white;
            font-family:Segoe UI;
            font-size:11pt;
        }

        QLabel#titulo{
            font-size:28px;
            font-weight:bold;
            color:#38BDF8;
        }

        QLineEdit{
            background:white;
            color:black;
            border-radius:6px;
            padding:8px;
        }

        QPushButton{
            background:#2563EB;
            color:white;
            border:none;
            border-radius:6px;
            padding:10px;
            font-size:13pt;
            font-weight:bold;
        }

        QPushButton:hover{
            background:#1D4ED8;
        }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        titulo = QLabel("SGM PIEDRA VIAL")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)

        subtitulo = QLabel("Sistema de Gestión de Mantenimiento")
        subtitulo.setAlignment(Qt.AlignCenter)

        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Usuario")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QLineEdit.Password)

        btn = QPushButton("INGRESAR")
        btn.clicked.connect(self.login)

        layout.addStretch()

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(self.usuario)
        layout.addWidget(self.password)
        layout.addWidget(btn)

        layout.addStretch()

        self.setLayout(layout)

    def login(self):

        usuario = self.usuario.text().strip()
        password = self.password.text().strip()

        conexion = sqlite3.connect(self.db)
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT nombre
            FROM usuarios
            WHERE usuario=?
            AND password=?
            AND estado=1
        """, (usuario, password))

        resultado = cursor.fetchone()

        conexion.close()

        if resultado:

            self.dashboard = Dashboard()
            self.dashboard.show()

            self.close()

        else:

            QMessageBox.warning(
                self,
                "Acceso denegado",
                "Usuario o contraseña incorrectos."
            )