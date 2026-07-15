from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt


class Inventario(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # ==========================
        # TITULO
        # ==========================

        titulo = QLabel("INVENTARIO DE REPUESTOS")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("""
            font-size:26px;
            font-weight:bold;
            color:#2563EB;
            margin:10px;
        """)

        layout.addWidget(titulo)

        # ==========================
        # TABLA
        # ==========================

        self.tabla = QTableWidget()

        self.tabla.setColumnCount(12)

        self.tabla.setHorizontalHeaderLabels([
            "Código",
            "Descripción",
            "N° Parte",
            "Marca",
            "Equipo",
            "Categoría",
            "Ubicación",
            "Stock",
            "Stock Min.",
            "Unidad",
            "Precio",
            "Proveedor"
        ])

        self.tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.tabla.setAlternatingRowColors(True)

        layout.addWidget(self.tabla)

        # ==========================
        # BOTONES
        # ==========================

        botones = QHBoxLayout()

        self.btnNuevo = QPushButton("➕ Nuevo")
        self.btnEditar = QPushButton("✏ Editar")
        self.btnEliminar = QPushButton("🗑 Eliminar")
        self.btnBuscar = QPushButton("🔎 Buscar")
        self.btnExcel = QPushButton("📄 Exportar Excel")

        botones.addWidget(self.btnNuevo)
        botones.addWidget(self.btnEditar)
        botones.addWidget(self.btnEliminar)
        botones.addWidget(self.btnBuscar)

        botones.addStretch()

        botones.addWidget(self.btnExcel)

        layout.addLayout(botones)

        self.cargar_datos()

    # ===================================
    # DATOS DE EJEMPLO
    # ===================================

    def cargar_datos(self):

        datos = [

            [
                "PV-0001",
                "Filtro de Aceite",
                "1R-1808",
                "CAT",
                "McCloskey J40",
                "Filtros",
                "ALM-01",
                5,
                2,
                "UND",
                185.50,
                "Ferreyros"
            ],

            [
                "PV-0002",
                "Rodamiento",
                "22220E",
                "SKF",
                "Pegson 1300",
                "Rodamientos",
                "ALM-02",
                8,
                3,
                "UND",
                420.00,
                "SKF Perú"
            ],

            [
                "PV-0003",
                "Faja Transportadora",
                "8V-5600",
                "Gates",
                "McCloskey S190",
                "Fajas",
                "ALM-01",
                12,
                4,
                "UND",
                980.00,
                "Gates Perú"
            ]

        ]

        self.tabla.setRowCount(len(datos))

        for fila, registro in enumerate(datos):

            for columna, valor in enumerate(registro):

                self.tabla.setItem(
                    fila,
                    columna,
                    QTableWidgetItem(str(valor))
                )