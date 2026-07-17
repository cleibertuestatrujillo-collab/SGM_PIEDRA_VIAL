import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGridLayout,
    QMessageBox,
    QScrollArea,
    QWidget,
    QFileDialog,
    QHBoxLayout,
)

from database.database import get_database

ASSETS_EQUIPOS = Path(__file__).resolve().parent.parent / "assets" / "equipos"

TIPOS_EQUIPO = [
    "",
    "Chancadora Primaria",
    "Chancadora Secundaria",
    "Chancadora Terciaria",
    "Zaranda",
    "Faja Transportadora",
    "Alimentador",
    "Generador",
    "Compresor",
    "Otro",
]

PROYECTOS = ["YAULI", "LIVITACA", "LURIN", "CALLAO", "OTRO"]

ESTADOS_UI = [
    ("🟢 Operativo", "Operativo"),
    ("🟡 En mantenimiento", "En mantenimiento"),
    ("🔴 Fuera de servicio", "Fuera de servicio"),
]


class EquipoForm(QDialog):

    def __init__(self, parent=None, equipo_id=None):
        super().__init__(parent)
        self.equipo_id = equipo_id
        self.db = get_database()
        self.setWindowTitle(
            "Editar Equipo" if equipo_id else "Nuevo Equipo"
        )
        self.resize(720, 640)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenedor = QWidget()
        layout = QGridLayout(contenedor)

        self.codigo = QLineEdit()
        self.nombre = QLineEdit()
        self.tipo = QComboBox()
        self.tipo.addItems(TIPOS_EQUIPO)
        self.marca = QLineEdit()
        self.modelo = QLineEdit()
        self.anio = QLineEdit()
        self.serie = QLineEdit()
        self.fabricante = QLineEdit()
        self.motor = QLineEdit()
        self.serie_motor = QLineEdit()
        self.potencia = QLineEdit()
        self.proyecto = QComboBox()
        self.proyecto.setEditable(True)
        self.proyecto.addItems(PROYECTOS)
        self.ubicacion = QLineEdit()
        self.estado = QComboBox()
        for etiqueta, valor in ESTADOS_UI:
            self.estado.addItem(etiqueta, valor)
        self.observaciones = QLineEdit()
        self.ruta_manual = QLineEdit()
        self.ruta_manual_partes = QLineEdit()
        self.ruta_plano_hidraulico = QLineEdit()
        self.ruta_plano_electrico = QLineEdit()

        fila = 0

        def agregar(etiqueta, widget):
            nonlocal fila
            layout.addWidget(QLabel(etiqueta), fila, 0)
            layout.addWidget(widget, fila, 1)
            fila += 1

        def agregar_archivo(etiqueta, campo):
            nonlocal fila
            layout.addWidget(QLabel(etiqueta), fila, 0)
            fila_btn = QHBoxLayout()
            fila_btn.addWidget(campo)
            btn = QPushButton("…")
            btn.setFixedWidth(36)
            btn.clicked.connect(
                lambda _=False, c=campo, t=etiqueta: self._elegir_archivo(c, t)
            )
            fila_btn.addWidget(btn)
            layout.addLayout(fila_btn, fila, 1)
            fila += 1

        agregar("Código *", self.codigo)
        agregar("Nombre *", self.nombre)
        agregar("Tipo", self.tipo)
        agregar("Marca", self.marca)
        agregar("Modelo", self.modelo)
        agregar("Año", self.anio)
        agregar("Serie", self.serie)
        agregar("Fabricante", self.fabricante)
        agregar("Motor", self.motor)
        agregar("Serie motor", self.serie_motor)
        agregar("Potencia", self.potencia)
        agregar("Proyecto", self.proyecto)
        agregar("Ubicación", self.ubicacion)
        agregar("Estado", self.estado)
        agregar("Observaciones", self.observaciones)
        agregar_archivo("Manual de Operación", self.ruta_manual)
        agregar_archivo("Manual de Partes", self.ruta_manual_partes)
        agregar_archivo("Plano Hidráulico", self.ruta_plano_hidraulico)
        agregar_archivo("Plano Eléctrico", self.ruta_plano_electrico)

        nota = QLabel(
            "El horómetro se registra solo desde la ficha técnica. "
            "Las fotografías se gestionan en la pestaña Fotografías."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color:#64748B;")
        layout.addWidget(nota, fila, 0, 1, 2)

        scroll.setWidget(contenedor)
        root = QGridLayout(self)
        root.addWidget(scroll, 0, 0, 1, 2)

        self.btnGuardar = QPushButton("💾 Guardar")
        self.btnCancelar = QPushButton("❌ Cancelar")
        root.addWidget(self.btnGuardar, 1, 0)
        root.addWidget(self.btnCancelar, 1, 1)

        self.btnCancelar.clicked.connect(self.reject)
        self.btnGuardar.clicked.connect(self.guardar)

        if self.equipo_id:
            self._cargar()

    def _elegir_archivo(self, campo: QLineEdit, titulo: str):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            titulo,
            str(Path.home()),
            "Documentos (*.pdf);;Imágenes (*.png *.jpg *.jpeg);;Todos (*.*)",
        )
        if ruta:
            campo.setText(ruta)

    def _set_combo_texto(self, combo: QComboBox, valor: str):
        valor = (valor or "").strip()
        if not valor:
            return
        i = combo.findText(valor)
        if i >= 0:
            combo.setCurrentIndex(i)
        elif combo.isEditable():
            combo.setEditText(valor)
        else:
            combo.addItem(valor)
            combo.setCurrentText(valor)

    def _set_estado(self, valor: str):
        valor = (valor or "Operativo").strip()
        for i in range(self.estado.count()):
            if self.estado.itemData(i) == valor:
                self.estado.setCurrentIndex(i)
                return
        self.estado.setCurrentIndex(0)

    def _cargar(self):
        row = self.db.obtener_equipo_por_id(self.equipo_id)
        if row is None:
            return
        self.codigo.setText(row["codigo"] or "")
        self.nombre.setText(row["nombre"] or "")
        self._set_combo_texto(self.tipo, row["tipo"] or "")
        self.marca.setText(row["marca"] or "")
        self.modelo.setText(row["modelo"] or "")
        self.anio.setText(row["anio"] or "")
        self.serie.setText(row["serie"] or "")
        self.fabricante.setText(row["fabricante"] or "")
        self.motor.setText(row["motor"] or "")
        self.serie_motor.setText(row["serie_motor"] or "")
        self.potencia.setText(row["potencia"] or "")
        self._set_combo_texto(self.proyecto, row["proyecto"] or "")
        self.ubicacion.setText(row["ubicacion"] or "")
        self._set_estado(row["estado"] or "Operativo")
        self.observaciones.setText(row["observaciones"] or "")
        self.ruta_manual.setText(row["ruta_manual"] or "")
        self.ruta_manual_partes.setText(row["ruta_manual_partes"] or "")
        hid = row["ruta_plano_hidraulico"] if "ruta_plano_hidraulico" in row.keys() else ""
        ele = row["ruta_plano_electrico"] if "ruta_plano_electrico" in row.keys() else ""
        self.ruta_plano_hidraulico.setText(hid or "")
        self.ruta_plano_electrico.setText(ele or "")

    def _leer_datos(self) -> dict:
        codigo = self.codigo.text().strip()
        nombre = self.nombre.text().strip()
        if not codigo:
            raise ValueError("El código es obligatorio.")
        if not nombre:
            raise ValueError("El nombre es obligatorio.")
        proyecto = self.proyecto.currentText().strip()
        if proyecto.upper() == "OTRO":
            proyecto = self.proyecto.lineEdit().text().strip() if self.proyecto.lineEdit() else ""

        return {
            "codigo": codigo,
            "nombre": nombre,
            "tipo": self.tipo.currentText().strip(),
            "marca": self.marca.text().strip(),
            "modelo": self.modelo.text().strip(),
            "anio": self.anio.text().strip(),
            "serie": self.serie.text().strip(),
            "fabricante": self.fabricante.text().strip(),
            "motor": self.motor.text().strip(),
            "serie_motor": self.serie_motor.text().strip(),
            "potencia": self.potencia.text().strip(),
            "proyecto": proyecto,
            "ubicacion": self.ubicacion.text().strip(),
            "estado": self.estado.currentData() or "Operativo",
            "observaciones": self.observaciones.text().strip(),
            "ruta_foto": "",
            "ruta_manual": self.ruta_manual.text().strip(),
            "ruta_manual_partes": self.ruta_manual_partes.text().strip(),
            "ruta_plano_hidraulico": self.ruta_plano_hidraulico.text().strip(),
            "ruta_plano_electrico": self.ruta_plano_electrico.text().strip(),
        }

    def _copiar_a_assets(self, datos: dict) -> dict:
        codigo = datos["codigo"]
        destino_dir = ASSETS_EQUIPOS / codigo
        destino_dir.mkdir(parents=True, exist_ok=True)

        def copiar(campo: str, subcarpeta: str):
            origen = datos.get(campo) or ""
            if not origen or not Path(origen).is_file():
                return origen
            p = Path(origen).resolve()
            try:
                rel = p.relative_to(ASSETS_EQUIPOS.resolve())
                return str(ASSETS_EQUIPOS / rel)
            except ValueError:
                pass
            nuevo = destino_dir / subcarpeta / p.name
            nuevo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, nuevo)
            return str(nuevo)

        datos["ruta_manual"] = copiar("ruta_manual", "documentos")
        datos["ruta_manual_partes"] = copiar("ruta_manual_partes", "documentos")
        datos["ruta_plano_hidraulico"] = copiar(
            "ruta_plano_hidraulico", "documentos"
        )
        datos["ruta_plano_electrico"] = copiar(
            "ruta_plano_electrico", "documentos"
        )
        return datos

    def guardar(self):
        try:
            datos = self._copiar_a_assets(self._leer_datos())
            if self.equipo_id:
                self.db.actualizar_equipo(self.equipo_id, datos)
                msg = "Equipo actualizado correctamente."
            else:
                self.equipo_id = self.db.insertar_equipo(datos)
                msg = "Equipo registrado correctamente."
            QMessageBox.information(self, "Correcto", msg)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
