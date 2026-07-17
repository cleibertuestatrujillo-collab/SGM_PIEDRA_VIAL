from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QDialog,
)

from database.database import get_database
from modules.equipo_form import EquipoForm
from modules.equipo_ficha import EquipoFichaDialog
from modules.equipo_export import exportar_equipos_excel


class Equipos(QWidget):

    ROLE_ID = Qt.ItemDataRole.UserRole

    def __init__(self):
        super().__init__()
        self.db = get_database()

        layout = QVBoxLayout(self)

        titulo = QLabel("GESTIÓN DE EQUIPOS")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("""
            font-size:26px;
            font-weight:bold;
            color:#2563EB;
            margin:10px;
        """)
        layout.addWidget(titulo)

        busqueda_layout = QHBoxLayout()
        busqueda_layout.addWidget(QLabel("Buscar:"))
        self.campo_busqueda = QLineEdit()
        self.campo_busqueda.setPlaceholderText(
            "Código, nombre, tipo, marca, proyecto, ubicación..."
        )
        self.campo_busqueda.setClearButtonEnabled(True)
        busqueda_layout.addWidget(self.campo_busqueda)
        layout.addLayout(busqueda_layout)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "Código",
            "Nombre",
            "Tipo",
            "Marca",
            "Modelo",
            "Proyecto",
            "Ubicación",
            "Horómetro",
            "Estado",
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        botones = QHBoxLayout()
        self.btnNuevo = QPushButton("➕ Nuevo")
        self.btnEditar = QPushButton("✏ Editar")
        self.btnEliminar = QPushButton("🗑 Eliminar")
        self.btnBuscar = QPushButton("🔎 Buscar")
        self.btnExcel = QPushButton("📊 Exportar Equipos a Excel")

        botones.addWidget(self.btnNuevo)
        botones.addWidget(self.btnEditar)
        botones.addWidget(self.btnEliminar)
        botones.addWidget(self.btnBuscar)
        botones.addStretch()
        botones.addWidget(self.btnExcel)
        layout.addLayout(botones)

        self.btnNuevo.clicked.connect(self.nuevo)
        self.btnEditar.clicked.connect(self.editar)
        self.btnEliminar.clicked.connect(self.eliminar)
        self.btnBuscar.clicked.connect(self.enfocar_busqueda)
        self.btnExcel.clicked.connect(self.exportar_excel)
        self.campo_busqueda.textChanged.connect(self.buscar_en_tiempo_real)
        self.tabla.cellDoubleClicked.connect(self._doble_clic_ficha)

        self.cargar_datos()

    def enfocar_busqueda(self):
        self.campo_busqueda.setFocus()
        self.campo_busqueda.selectAll()

    def cargar_datos(self):
        termino = self.campo_busqueda.text()
        filas = self.db.buscar_equipos(termino)
        self.tabla.setRowCount(len(filas))

        for fila_idx, row in enumerate(filas):
            valores = [
                row["codigo"],
                row["nombre"],
                row["tipo"],
                row["marca"],
                row["modelo"],
                row["proyecto"],
                row["ubicacion"],
                self.db.obtener_horometro_actual(row["id"]),
                row["estado"],
            ]
            for col_idx, valor in enumerate(valores):
                texto = "" if valor is None else str(valor)
                item = QTableWidgetItem(texto)
                if col_idx == 0:
                    item.setData(self.ROLE_ID, row["id"])
                self.tabla.setItem(fila_idx, col_idx, item)

    def buscar_en_tiempo_real(self):
        self.cargar_datos()

    def _equipo_id_seleccionado(self):
        sel = self.tabla.selectionModel().selectedRows()
        if not sel:
            return None
        item = self.tabla.item(sel[0].row(), 0)
        return item.data(self.ROLE_ID) if item else None

    def _doble_clic_ficha(self, row: int, _col: int):
        item = self.tabla.item(row, 0)
        if item is None:
            return
        equipo_id = item.data(self.ROLE_ID)
        if equipo_id is None:
            return
        try:
            dlg = EquipoFichaDialog(equipo_id, self)
            dlg.exec()
            self.cargar_datos()
        except ValueError as e:
            QMessageBox.warning(self, "Ficha", str(e))

    def nuevo(self):
        dlg = EquipoForm(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def editar(self):
        equipo_id = self._equipo_id_seleccionado()
        if equipo_id is None:
            QMessageBox.warning(
                self, "Editar", "Seleccione un equipo de la tabla."
            )
            return
        dlg = EquipoForm(self, equipo_id=equipo_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def eliminar(self):
        equipo_id = self._equipo_id_seleccionado()
        if equipo_id is None:
            QMessageBox.warning(
                self, "Eliminar", "Seleccione un equipo de la tabla."
            )
            return
        fila = self.tabla.selectionModel().selectedRows()[0].row()
        codigo = self.tabla.item(fila, 0).text()
        nombre = self.tabla.item(fila, 1).text()
        ok = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar el equipo?\n\n{codigo} — {nombre}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.eliminar_equipo(equipo_id)
            self.cargar_datos()
            QMessageBox.information(
                self, "Eliminado", "Equipo eliminado correctamente."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def exportar_excel(self):
        exportar_equipos_excel(self.db, self)
