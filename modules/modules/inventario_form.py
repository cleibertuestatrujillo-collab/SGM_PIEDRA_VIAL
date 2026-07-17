from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGridLayout,
    QMessageBox,
)

from database.database import get_database, normalizar_moneda


class InventarioForm(QDialog):

    _UBICACIONES_PREDEFINIDAS = (
        "ALM-LURIN",
        "ALM-CALLAO",
        "ALM-LIVITACA",
        "OTRO...",
    )

    def __init__(self, parent=None, repuesto_id=None):
        super().__init__(parent)

        self.repuesto_id = repuesto_id
        self.db = get_database()

        self.setWindowTitle(
            "Editar Repuesto" if repuesto_id else "Nuevo Repuesto"
        )
        self.resize(700, 520)

        layout = QGridLayout()

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
            "Kleemann MCO90i",
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
            "Zaranda",
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
            "Otro",
        ])

        self.ubicacion = QComboBox()
        self.ubicacion.setEditable(True)
        self.ubicacion.addItems(list(self._UBICACIONES_PREDEFINIDAS))
        self.ubicacion.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        linea_ubicacion = self.ubicacion.lineEdit()
        if linea_ubicacion is not None:
            linea_ubicacion.setPlaceholderText("Seleccione o escriba ubicación")
        self.ubicacion.activated.connect(self._on_ubicacion_seleccionada)

        self.stock = QLineEdit("0")
        self.stock_min = QLineEdit("0")
        self.unidad = QComboBox()
        self.unidad.addItems(["UND", "KIT", "LT", "KG", "M", "ROLLO"])

        self.precio = QLineEdit("0")
        self.moneda = QComboBox()
        self.moneda.addItem("$ USD - Dólares", "USD")
        self.moneda.addItem("S/ PEN - Soles", "PEN")
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
        agregar("Moneda", self.moneda)
        agregar("Precio", self.precio)
        agregar("Proveedor", self.proveedor)
        agregar("Observaciones", self.observacion)

        self.btnGuardar = QPushButton("💾 Guardar")
        self.btnCancelar = QPushButton("❌ Cancelar")

        layout.addWidget(self.btnGuardar, fila, 0)
        layout.addWidget(self.btnCancelar, fila, 1)

        self.setLayout(layout)

        self.btnCancelar.clicked.connect(self.reject)
        self.btnGuardar.clicked.connect(self.guardar)

        if self.repuesto_id:
            self._cargar_repuesto()

    def _on_ubicacion_seleccionada(self, index: int):
        if self.ubicacion.itemText(index) != "OTRO...":
            return
        self.ubicacion.setEditText("")
        linea = self.ubicacion.lineEdit()
        if linea is not None:
            linea.setPlaceholderText("Escriba la ubicación personalizada")
            linea.setFocus()

    def _set_ubicacion(self, text: str):
        text = (text or "").strip()
        if not text:
            self.ubicacion.setCurrentIndex(0)
            return
        idx = self.ubicacion.findText(text)
        if idx >= 0:
            self.ubicacion.setCurrentIndex(idx)
        else:
            self.ubicacion.setEditText(text)

    def _set_combo_text(self, combo: QComboBox, text: str):
        if not text:
            combo.setCurrentIndex(0)
            return
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.addItem(text)
            combo.setCurrentText(text)

    def _set_moneda(self, codigo: str):
        codigo = normalizar_moneda(codigo)
        idx = self.moneda.findData(codigo)
        if idx >= 0:
            self.moneda.setCurrentIndex(idx)
        else:
            self.moneda.setCurrentIndex(0)

    def _cargar_repuesto(self):
        row = self.db.obtener_repuesto_por_id(self.repuesto_id)
        if row is None:
            return

        self.codigo.setText(row["codigo"] or "")
        self.descripcion.setText(row["descripcion"] or "")
        self.numero_parte.setText(row["numero_parte"] or "")
        self.marca.setText(row["marca"] or "")
        self._set_combo_text(self.equipo, row["equipo"] or "")
        self._set_combo_text(self.sistema, row["sistema"] or "")
        self._set_combo_text(self.categoria, row["categoria"] or "")
        self._set_ubicacion(row["ubicacion"] or "")
        self.stock.setText(str(row["stock"] if row["stock"] is not None else 0))
        self.stock_min.setText(str(row["stock_min"] if row["stock_min"] is not None else 0))
        self._set_combo_text(self.unidad, row["unidad"] or "UND")
        moneda = row["moneda"] if "moneda" in row.keys() else "USD"
        self._set_moneda(moneda)
        self.precio.setText(str(row["precio"] if row["precio"] is not None else 0))
        self.proveedor.setText(row["proveedor"] or "")
        self.observacion.setText(row["observacion"] or "")

    def _leer_datos(self):
        codigo = self.codigo.text().strip()
        descripcion = self.descripcion.text().strip()
        if not codigo:
            raise ValueError("El código es obligatorio.")
        if not descripcion:
            raise ValueError("La descripción es obligatoria.")

        try:
            stock = float(self.stock.text().strip() or "0")
            stock_min = float(self.stock_min.text().strip() or "0")
            precio = float(self.precio.text().strip() or "0")
        except ValueError as exc:
            raise ValueError(
                "Stock, stock mínimo y precio deben ser numéricos."
            ) from exc

        ubicacion = self.ubicacion.currentText().strip()
        if ubicacion == "OTRO...":
            raise ValueError(
                "Seleccionó «OTRO...». Escriba la ubicación personalizada."
            )

        return {
            "codigo": codigo,
            "descripcion": descripcion,
            "numero_parte": self.numero_parte.text().strip(),
            "marca": self.marca.text().strip(),
            "equipo": self.equipo.currentText().strip(),
            "sistema": self.sistema.currentText().strip(),
            "categoria": self.categoria.currentText().strip(),
            "ubicacion": ubicacion,
            "stock": stock,
            "stock_min": stock_min,
            "unidad": self.unidad.currentText().strip() or "UND",
            "precio": precio,
            "moneda": self.moneda.currentData() or "USD",
            "proveedor": self.proveedor.text().strip(),
            "observacion": self.observacion.text().strip(),
        }

    def guardar(self):
        try:
            datos = self._leer_datos()
            if self.repuesto_id:
                self.db.actualizar_repuesto(self.repuesto_id, datos)
                mensaje = "Repuesto actualizado correctamente."
            else:
                self.db.insertar_repuesto(datos)
                mensaje = "Repuesto registrado correctamente."

            QMessageBox.information(self, "Correcto", mensaje)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
