from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGridLayout,
    QMessageBox
)

import sqlite3
from pathlib import Path


class InventarioForm(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nuevo Repuesto")
        self.resize(700,520)

        self.db = Path(__file__).parent.parent / "database" / "sgm.db"

        layout = QGridLayout()

        # ==========================
        # CAMPOS
        # ==========================

        self.codigo = QLineEdit()
        self.descripcion = QLineEdit()
        self.numero_parte = QLineEdit()
        self.marca = QLineEdit()

        self.equipo = QComboBox()
        self.equipo.addItems([
            "",
            "McCloskey J40",
            "Pegson 1300",
            "McCloskey S190",
            "McCloskey V80",
            "Kleemann MCO90i"
        ])

        self.sistema = QComboBox()
        self.sistema.addItems([
            "",
            "Motor",
            "Alimentador",
            "Faja Principal",
            "Faja Lateral",
            "Cono",
            "Chasis",
            "Sistema Hidráulico",
            "Sistema Eléctrico",
            "Zaranda"
        ])

        self.categoria = QComboBox()
        self.categoria.addItems([
            "",
            "Rodamiento",
            "Chumacera",
            "Filtro",
            "Sensor",
            "Banda",
            "Motor",
            "Polea",
            "Perno",
            "Manguera",
            "Aceite",
            "Grasa",
            "Otro"
        ])

        self.ubicacion = QComboBox()
        self.ubicacion.addItems([
            "ALM-01",
            "ALM-02",
            "ALM-03",
            "TALLER",
            "OBRA"
        ])

        self.stock = QLineEdit("0")
        self.stock_min = QLineEdit("0")
        self.unidad = QComboBox()
        self.unidad.addItems(["UND","KIT","LT","KG","M","ROLLO"])

        self.precio = QLineEdit("0")
        self.proveedor = QLineEdit()
        self.observacion = QLineEdit()

        fila = 0

        def agregar(nombre, widget):
            nonlocal fila
            layout.addWidget(QLabel(nombre), fila, 0)
            layout.addWidget(widget, fila, 1)
            fila += 1

        agregar("Código", self.codigo)
        agregar("Descripción", self.descripcion)
        agregar("Número de Parte", self.numero_parte)
        agregar("Marca", self.marca)
        agregar("Equipo", self.equipo)
        agregar("Sistema", self.sistema)
        agregar("Categoría", self.categoria)
        agregar("Ubicación", self.ubicacion)
        agregar("Stock", self.stock)
        agregar("Stock Mínimo", self.stock_min)
        agregar("Unidad", self.unidad)
        agregar("Precio", self.precio)
        agregar("Proveedor", self.proveedor)
        agregar("Observaciones", self.observacion)

        self.btnGuardar = QPushButton("💾 Guardar")
        self.btnCancelar = QPushButton("❌ Cancelar")

        layout.addWidget(self.btnGuardar, fila,0)
        layout.addWidget(self.btnCancelar, fila,1)

        self.setLayout(layout)

        self.btnCancelar.clicked.connect(self.close)
        self.btnGuardar.clicked.connect(self.guardar)

    def guardar(self):

        try:

            con = sqlite3.connect(self.db)
            cur = con.cursor()

            cur.execute("""
            INSERT INTO inventario
            (
                codigo,
                descripcion,
                numero_parte,
                marca,
                equipo,
                categoria,
                ubicacion,
                stock,
                stock_min,
                precio,
                proveedor
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)
            """,(

                self.codigo.text(),
                self.descripcion.text(),
                self.numero_parte.text(),
                self.marca.text(),
                self.equipo.currentText(),
                self.categoria.currentText(),
                self.ubicacion.currentText(),
                float(self.stock.text()),
                float(self.stock_min.text()),
                float(self.precio.text()),
                self.proveedor.text()

            ))

            con.commit()
            con.close()

            QMessageBox.information(
                self,
                "Correcto",
                "Repuesto registrado correctamente."
            )

            self.accept()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )