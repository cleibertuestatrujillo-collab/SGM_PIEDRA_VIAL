from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGridLayout,
    QMessageBox,
    QDateTimeEdit,
)
from PySide6.QtCore import QDateTime

from database.database import get_database, normalizar_moneda


class KardexMovimientoForm(QDialog):

    def __init__(
        self,
        parent=None,
        inventario_id: int | None = None,
        tipo: str = "ENTRADA",
    ):
        super().__init__(parent)

        self.inventario_id = inventario_id
        self.tipo = tipo.upper()
        self.db = get_database()

        es_entrada = self.tipo == "ENTRADA"
        self.setWindowTitle("Entrada de stock" if es_entrada else "Salida de stock")
        self.resize(520, 380)

        layout = QGridLayout()
        fila = 0

        rep = None
        if inventario_id:
            rep = self.db.obtener_repuesto_por_id(inventario_id)

        self.lbl_repuesto = QLabel(
            f"{rep['codigo']} — {rep['descripcion']}" if rep else "—"
        )
        layout.addWidget(QLabel("Repuesto"), fila, 0)
        layout.addWidget(self.lbl_repuesto, fila, 1)
        fila += 1

        self.fecha = QDateTimeEdit(QDateTime.currentDateTime())
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        layout.addWidget(QLabel("Fecha"), fila, 0)
        layout.addWidget(self.fecha, fila, 1)
        fila += 1

        self.cantidad = QLineEdit()
        self.cantidad.setPlaceholderText("Cantidad")
        layout.addWidget(QLabel("Cantidad"), fila, 0)
        layout.addWidget(self.cantidad, fila, 1)
        fila += 1

        self.costo_unitario = QLineEdit()
        self.moneda = QComboBox()
        self.moneda.addItem("$ USD - Dólares", "USD")
        self.moneda.addItem("S/ PEN - Soles", "PEN")

        if rep:
            moneda = normalizar_moneda(
                rep["moneda"] if "moneda" in rep.keys() else "USD"
            )
            idx = self.moneda.findData(moneda)
            if idx >= 0:
                self.moneda.setCurrentIndex(idx)
            self.costo_unitario.setText(
                str(rep["precio"] if rep["precio"] is not None else 0)
            )

        if es_entrada:
            layout.addWidget(QLabel("Costo unitario"), fila, 0)
            layout.addWidget(self.costo_unitario, fila, 1)
            fila += 1
            layout.addWidget(QLabel("Moneda"), fila, 0)
            layout.addWidget(self.moneda, fila, 1)
            fila += 1
        else:
            self.costo_unitario.hide()
            self.moneda.hide()

        self.documento = QLineEdit()
        self.documento.setPlaceholderText("Guía, factura, OT...")
        layout.addWidget(QLabel("Documento"), fila, 0)
        layout.addWidget(self.documento, fila, 1)
        fila += 1

        self.observacion = QLineEdit()
        layout.addWidget(QLabel("Observación"), fila, 0)
        layout.addWidget(self.observacion, fila, 1)
        fila += 1

        self.btn_guardar = QPushButton("💾 Registrar")
        self.btn_cancelar = QPushButton("❌ Cancelar")
        layout.addWidget(self.btn_guardar, fila, 0)
        layout.addWidget(self.btn_cancelar, fila, 1)

        self.setLayout(layout)

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar.clicked.connect(self.guardar)

    def guardar(self):
        if not self.inventario_id:
            QMessageBox.warning(self, "Kardex", "Seleccione un repuesto.")
            return

        try:
            cantidad = float(self.cantidad.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Kardex", "Cantidad inválida.")
            return

        fecha = self.fecha.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        documento = self.documento.text().strip()
        observacion = self.observacion.text().strip()

        try:
            if self.tipo == "ENTRADA":
                costo = float(
                    self.costo_unitario.text().strip().replace(",", ".") or "0"
                )
                moneda = self.moneda.currentData() or "USD"
                self.db.registrar_entrada_kardex(
                    self.inventario_id,
                    cantidad,
                    costo,
                    moneda=moneda,
                    documento=documento,
                    observacion=observacion,
                    fecha=fecha,
                )
            else:
                self.db.registrar_salida_kardex(
                    self.inventario_id,
                    cantidad,
                    documento=documento,
                    observacion=observacion,
                    fecha=fecha,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
