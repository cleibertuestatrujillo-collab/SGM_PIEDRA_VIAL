from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QStackedWidget
)

from PySide6.QtCore import Qt

from modules.inventario import Inventario


class Dashboard(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SGM Piedra Vial")
        self.resize(1300, 750)

        self.setStyleSheet("""
        QWidget{
            background:#F1F5F9;
            font-family:Segoe UI;
            font-size:11pt;
        }

        #menu{
            background:#1E293B;
        }

        QPushButton{
            background:#334155;
            color:white;
            border:none;
            padding:12px;
            text-align:left;
            border-radius:6px;
            font-size:12pt;
        }

        QPushButton:hover{
            background:#2563EB;
        }

        QLabel#logo{
            color:white;
            font-size:24px;
            font-weight:bold;
        }

        #contenido{
            background:white;
            border-radius:10px;
        }
        """)

        principal = QHBoxLayout(self)

        # =========================
        # MENÚ
        # =========================

        menu = QFrame()
        menu.setObjectName("menu")
        menu.setFixedWidth(240)

        menu_layout = QVBoxLayout(menu)

        logo = QLabel("SGM\nPIEDRA VIAL")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignCenter)

        menu_layout.addWidget(logo)
        menu_layout.addSpacing(20)

        self.btnInventario = QPushButton("📦 Inventario")
        self.btnKardex = QPushButton("🔄 Kardex")
        self.btnEquipos = QPushButton("🚜 Equipos")
        self.btnMantenimiento = QPushButton("🔧 Mantenimientos")
        self.btnCompras = QPushButton("🛒 Compras")
        self.btnReportes = QPushButton("📊 Reportes")
        self.btnConfig = QPushButton("⚙ Configuración")
        self.btnSalir = QPushButton("❌ Salir")

        menu_layout.addWidget(self.btnInventario)
        menu_layout.addWidget(self.btnKardex)
        menu_layout.addWidget(self.btnEquipos)
        menu_layout.addWidget(self.btnMantenimiento)
        menu_layout.addWidget(self.btnCompras)
        menu_layout.addWidget(self.btnReportes)
        menu_layout.addWidget(self.btnConfig)

        menu_layout.addStretch()

        menu_layout.addWidget(self.btnSalir)

        # =========================
        # CONTENIDO
        # =========================

        contenido = QFrame()
        contenido.setObjectName("contenido")

        contenido_layout = QVBoxLayout(contenido)

        self.paginas = QStackedWidget()

        # Página Inicio

        inicio = QWidget()

        inicio_layout = QVBoxLayout(inicio)

        titulo = QLabel("Bienvenido al Sistema SGM Piedra Vial")
        titulo.setStyleSheet("font-size:26px;font-weight:bold;")

        inicio_layout.addWidget(titulo)

        inicio_layout.addSpacing(20)

        inicio_layout.addWidget(QLabel("Seleccione un módulo del menú lateral."))

        inicio_layout.addStretch()

        # Página Inventario

        self.inventario = Inventario()

        self.paginas.addWidget(inicio)
        self.paginas.addWidget(self.inventario)

        contenido_layout.addWidget(self.paginas)

        principal.addWidget(menu)
        principal.addWidget(contenido)

        # =========================
        # EVENTOS
        # =========================

        self.btnInventario.clicked.connect(self.abrirInventario)
        self.btnSalir.clicked.connect(self.close)

    def abrirInventario(self):
        self.paginas.setCurrentIndex(1)