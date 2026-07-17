import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLineEdit,
    QFormLayout,
    QMessageBox,
    QScrollArea,
    QFrame,
    QComboBox,
    QGridLayout,
    QFileDialog,
)

from database.database import get_database
from modules.equipo_form import EquipoForm, ASSETS_EQUIPOS
from modules.equipo_utils import (
    proximo_pm_horas,
    semaforo_pm,
    estilo_tarjeta,
    semaforo_estado_equipo,
    icono_tipo_archivo,
    SEMAFORO_ESTILO,
)
from modules.equipo_export import exportar_ficha_pdf, exportar_equipos_excel

CATEGORIAS_FOTO = [
    "Equipo",
    "Motor",
    "Placa de serie",
    "Horómetro",
    "Daños",
]

DOCUMENTOS_FICHA = (
    ("Manual de Operación", "ruta_manual"),
    ("Manual de Partes", "ruta_manual_partes"),
    ("Plano Hidráulico", "ruta_plano_hidraulico"),
    ("Plano Eléctrico", "ruta_plano_electrico"),
)


class MiniaturaFoto(QLabel):
    def __init__(self, ruta: str, parent=None):
        super().__init__(parent)
        self.ruta = ruta
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            VisorImagenDialog(self.ruta, self.window()).exec()
        super().mouseDoubleClickEvent(event)


class VisorImagenDialog(QDialog):
    def __init__(self, ruta: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Path(ruta).name)
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(ruta)
        if not pix.isNull():
            lbl.setPixmap(
                pix.scaled(
                    760, 560,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            lbl.setText("No se pudo cargar la imagen.")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        QVBoxLayout(cont).addWidget(lbl)
        scroll.setWidget(cont)
        layout.addWidget(scroll)


class EquipoFichaDialog(QDialog):

    def __init__(self, equipo_id: int, parent=None, usuario: str = "admin"):
        super().__init__(parent)
        self.equipo_id = equipo_id
        self.usuario = usuario or "admin"
        self.db = get_database()
        self._canvas_horometro = None

        row = self.db.obtener_equipo_por_id(equipo_id)
        if row is None:
            raise ValueError("Equipo no encontrado.")

        self.setWindowTitle(f"Ficha técnica — {row['codigo']} {row['nombre']}")
        self.resize(1000, 720)

        layout = QVBoxLayout(self)
        self.lbl_encabezado = QLabel()
        layout.addWidget(self.lbl_encabezado)

        dash_scroll = QScrollArea()
        dash_scroll.setWidgetResizable(True)
        dash_scroll.setMaximumHeight(130)
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QHBoxLayout(self.dashboard_widget)
        dash_scroll.setWidget(self.dashboard_widget)
        layout.addWidget(dash_scroll)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        botones = QHBoxLayout()
        btn_mant = QPushButton("Ver mantenimientos")
        btn_mant.clicked.connect(self._ver_mantenimientos)
        btn_pdf = QPushButton("📄 Exportar ficha PDF")
        btn_pdf.clicked.connect(self._exportar_pdf)
        btn_xls = QPushButton("📊 Exportar Equipos a Excel")
        btn_xls.clicked.connect(
            lambda: exportar_equipos_excel(self.db, self)
        )
        btn_editar = QPushButton("✏ Editar equipo")
        btn_editar.clicked.connect(self._editar_equipo)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        botones.addWidget(btn_mant)
        botones.addWidget(btn_pdf)
        botones.addWidget(btn_xls)
        botones.addStretch()
        botones.addWidget(btn_editar)
        botones.addWidget(btn_cerrar)
        layout.addLayout(botones)

        self._refrescar_vista()

    def _row(self):
        return self.db.obtener_equipo_por_id(self.equipo_id)

    def _refrescar_vista(self):
        row = self._row()
        self.lbl_encabezado.setText(
            f"<span style='font-size:22px;font-weight:bold;color:#2563EB;'>"
            f"{row['codigo']}</span> — {row['nombre']}"
        )
        self._refrescar_dashboard()
        self.tabs.clear()
        self._canvas_horometro = None
        self.tabs.addTab(self._tab_datos_generales(row), "Datos generales")
        self.tabs.addTab(self._tab_motor(row), "Motor")
        self.tabs.addTab(self._tab_horometro(), "Horómetro")
        self.tabs.addTab(self._tab_repuestos(), "Repuestos compatibles")
        self.tabs.addTab(
            self._tab_mantenimientos(), "Historial de mantenimientos"
        )
        self.tabs.addTab(self._tab_inspecciones(), "Inspecciones")
        self.tabs.addTab(self._tab_documentos(row), "Documentos")
        self.tabs.addTab(self._tab_fotografias(), "Fotografías")

    def _tarjeta(self, titulo: str, valor: str, semaforo: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(estilo_tarjeta(semaforo))
        vl = QVBoxLayout(frame)
        t = QLabel(f"<b>{titulo}</b>")
        v = QLabel(str(valor))
        v.setWordWrap(True)
        _, etiqueta = SEMAFORO_ESTILO.get(semaforo, SEMAFORO_ESTILO["ok"])
        if titulo.startswith("Próximo PM"):
            v.setText(f"{valor}\n<small>{etiqueta}</small>")
            v.setTextFormat(Qt.TextFormat.RichText)
        vl.addWidget(t)
        vl.addWidget(v)
        return frame

    def _refrescar_dashboard(self):
        while self.dashboard_layout.count():
            item = self.dashboard_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row = self._row()
        horo = self.db.obtener_horometro_actual(self.equipo_id)
        estado = row["estado"] or "Operativo"
        proyecto = row["proyecto"] or "—"

        self.dashboard_layout.addWidget(
            self._tarjeta(
                "Horómetro actual",
                f"{horo:.1f} h",
                "ok",
            )
        )
        self.dashboard_layout.addWidget(
            self._tarjeta(
                "Estado",
                estado,
                semaforo_estado_equipo(estado),
            )
        )
        self.dashboard_layout.addWidget(
            self._tarjeta("Proyecto", proyecto, "ok")
        )

        for intervalo in (250, 500, 1000):
            prox = proximo_pm_horas(horo, intervalo)
            sem = semaforo_pm(horo, prox)
            self.dashboard_layout.addWidget(
                self._tarjeta(
                    f"Próximo PM{intervalo}",
                    f"{prox:.0f} h",
                    sem,
                )
            )
        self.dashboard_layout.addStretch()

    def _fila(self, layout: QFormLayout, titulo: str, valor):
        texto = "" if valor is None else str(valor)
        layout.addRow(titulo, QLabel(texto))

    def _tab_datos_generales(self, row) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._fila(form, "Código", row["codigo"])
        self._fila(form, "Nombre", row["nombre"])
        self._fila(form, "Tipo", row["tipo"])
        self._fila(form, "Marca", row["marca"])
        self._fila(form, "Modelo", row["modelo"])
        self._fila(form, "Año", row["anio"])
        self._fila(form, "Serie", row["serie"])
        self._fila(form, "Fabricante", row["fabricante"])
        self._fila(form, "Proyecto", row["proyecto"])
        self._fila(form, "Ubicación", row["ubicacion"])
        self._fila(form, "Estado", row["estado"])
        self._fila(form, "Observaciones", row["observaciones"])
        horo = self.db.obtener_horometro_actual(self.equipo_id)
        self._fila(form, "Horómetro actual (última lectura)", horo)
        cr = row["costo_repuestos"] if "costo_repuestos" in row.keys() else 0
        cm = row["costo_mano_obra"] if "costo_mano_obra" in row.keys() else 0
        ct = row["costo_total"] if "costo_total" in row.keys() else 0
        self._fila(form, "Costo repuestos (acum.)", cr)
        self._fila(form, "Costo mano de obra (acum.)", cm)
        self._fila(form, "Costo total (acum.)", ct)
        return w

    def _tab_motor(self, row) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._fila(form, "Motor", row["motor"])
        self._fila(form, "Serie motor", row["serie_motor"])
        self._fila(form, "Potencia", row["potencia"])
        self._fila(form, "Fabricante", row["fabricante"])
        return w

    def _tab_horometro(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        actual = self.db.obtener_horometro_actual(self.equipo_id)
        registro = QHBoxLayout()
        self.input_horometro = QLineEdit(str(actual))
        self.input_usuario_hor = QLineEdit(self.usuario)
        self.input_obs_hor = QLineEdit()
        self.input_obs_hor.setPlaceholderText("Observación (opcional)")
        btn_reg = QPushButton("Registrar lectura")
        btn_reg.clicked.connect(self._registrar_horometro)
        registro.addWidget(QLabel("Nueva lectura:"))
        registro.addWidget(self.input_horometro)
        registro.addWidget(self.input_usuario_hor)
        registro.addWidget(self.input_obs_hor)
        registro.addWidget(btn_reg)
        layout.addLayout(registro)

        self.grafico_container = QWidget()
        self.grafico_layout = QVBoxLayout(self.grafico_container)
        layout.addWidget(self.grafico_container)
        self._dibujar_grafico_horometro()

        self.tabla_horometro = QTableWidget()
        self.tabla_horometro.setColumnCount(4)
        self.tabla_horometro.setHorizontalHeaderLabels(
            ["Fecha", "Horómetro", "Usuario", "Observación"]
        )
        self.tabla_horometro.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.tabla_horometro)
        self._cargar_horometro()
        return w

    def _dibujar_grafico_horometro(self):
        while self.grafico_layout.count():
            item = self.grafico_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._canvas_horometro = None

        filas = list(reversed(self.db.obtener_historial_horometro(self.equipo_id)))
        if not filas:
            self.grafico_layout.addWidget(
                QLabel("Sin datos para el gráfico. Registre lecturas.")
            )
            return

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            fechas = [r["fecha"][:10] for r in filas]
            horas = [float(r["horometro"]) for r in filas]

            fig = Figure(figsize=(8, 2.8), tight_layout=True)
            ax = fig.add_subplot(111)
            ax.plot(fechas, horas, marker="o", color="#2563EB", linewidth=2)
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Horas")
            ax.set_title("Evolución del horómetro")
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate(rotation=30)

            canvas = FigureCanvasQTAgg(fig)
            self._canvas_horometro = canvas
            self.grafico_layout.addWidget(canvas)
        except ImportError:
            self.grafico_layout.addWidget(
                QLabel("Instale matplotlib para ver el gráfico.")
            )

    def _cargar_horometro(self):
        if not hasattr(self, "tabla_horometro"):
            return
        filas = self.db.obtener_historial_horometro(self.equipo_id)
        self.tabla_horometro.setRowCount(len(filas))
        for i, r in enumerate(filas):
            self.tabla_horometro.setItem(i, 0, QTableWidgetItem(r["fecha"]))
            self.tabla_horometro.setItem(
                i, 1, QTableWidgetItem(str(r["horometro"]))
            )
            self.tabla_horometro.setItem(
                i, 2, QTableWidgetItem(r["usuario"] or "")
            )
            self.tabla_horometro.setItem(
                i, 3, QTableWidgetItem(r["observacion"] or "")
            )

    def _registrar_horometro(self):
        try:
            valor = float(self.input_horometro.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Horómetro", "Ingrese un valor numérico.")
            return
        self.db.registrar_horometro_equipo(
            self.equipo_id,
            valor,
            self.input_obs_hor.text().strip(),
            self.input_usuario_hor.text().strip() or self.usuario,
        )
        self._refrescar_dashboard()
        self._cargar_horometro()
        self._dibujar_grafico_horometro()
        QMessageBox.information(self, "Horómetro", "Lectura registrada.")

    def _tab_repuestos(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabla_repuestos = QTableWidget()
        self.tabla_repuestos.setColumnCount(6)
        self.tabla_repuestos.setHorizontalHeaderLabels([
            "Código", "Descripción", "N° Parte", "Stock", "Unidad", "Notas",
        ])
        self.tabla_repuestos.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.tabla_repuestos)
        filas = self.db.obtener_repuestos_compatibles_equipo(self.equipo_id)
        self.tabla_repuestos.setRowCount(len(filas))
        for i, r in enumerate(filas):
            self.tabla_repuestos.setItem(i, 0, QTableWidgetItem(r["codigo"]))
            self.tabla_repuestos.setItem(
                i, 1, QTableWidgetItem(r["descripcion"] or "")
            )
            self.tabla_repuestos.setItem(
                i, 2, QTableWidgetItem(r["numero_parte"] or "")
            )
            self.tabla_repuestos.setItem(
                i, 3, QTableWidgetItem(str(r["stock"]))
            )
            self.tabla_repuestos.setItem(
                i, 4, QTableWidgetItem(r["unidad"] or "")
            )
            notas = r["notas"] if "notas" in r.keys() else ""
            self.tabla_repuestos.setItem(i, 5, QTableWidgetItem(notas or ""))
        return w

    def _tab_mantenimientos(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        tabla = QTableWidget()
        tabla.setColumnCount(6)
        tabla.setHorizontalHeaderLabels([
            "Fecha", "Horómetro", "Tipo", "Descripción", "Costo", "Responsable",
        ])
        tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(tabla)
        filas = self.db.obtener_mantenimientos_equipo(self.equipo_id)
        tabla.setRowCount(len(filas))
        for i, r in enumerate(filas):
            tabla.setItem(i, 0, QTableWidgetItem(r["fecha"] or ""))
            tabla.setItem(i, 1, QTableWidgetItem(str(r["horometro"] or "")))
            tabla.setItem(i, 2, QTableWidgetItem(r["tipo"] or ""))
            tabla.setItem(i, 3, QTableWidgetItem(r["descripcion"] or ""))
            tabla.setItem(i, 4, QTableWidgetItem(str(r["costo"] or "")))
            tabla.setItem(i, 5, QTableWidgetItem(r["responsable"] or ""))
        return w

    def _tab_inspecciones(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(
            QLabel(
                "Listado de inspecciones (checklists diarios — módulo futuro)."
            )
        )
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels([
            "Fecha", "Tipo", "Resultado", "Observación", "Usuario",
        ])
        tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(tabla)
        filas = self.db.obtener_inspecciones_equipo(self.equipo_id)
        tabla.setRowCount(len(filas))
        for i, r in enumerate(filas):
            tabla.setItem(i, 0, QTableWidgetItem(r["fecha"] or ""))
            tabla.setItem(i, 1, QTableWidgetItem(r["tipo"] or ""))
            tabla.setItem(i, 2, QTableWidgetItem(r["resultado"] or ""))
            tabla.setItem(i, 3, QTableWidgetItem(r["observacion"] or ""))
            tabla.setItem(i, 4, QTableWidgetItem(r["usuario"] or ""))
        return w

    def _tab_documentos(self, row) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self._doc_layout = layout
        self._pintar_documentos(row)
        return w

    def _pintar_documentos(self, row):
        while self._doc_layout.count():
            item = self._doc_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for titulo, clave in DOCUMENTOS_FICHA:
            ruta = row[clave] if clave in row.keys() else ""
            fila = QHBoxLayout()
            fila.addWidget(QLabel(f"<b>{titulo}</b>"))
            fila.addWidget(QLabel(icono_tipo_archivo(ruta)))
            nombre = Path(ruta).name if ruta else "(sin archivo)"
            fila.addWidget(QLabel(nombre), 1)
            btn_adj = QPushButton("Adjuntar")
            btn_adj.clicked.connect(
                lambda _=False, k=clave: self._adjuntar_documento(k)
            )
            fila.addWidget(btn_adj)
            if ruta and Path(ruta).is_file():
                btn = QPushButton("Abrir")
                btn.clicked.connect(
                    lambda _=False, p=ruta: self._abrir_archivo(p)
                )
                fila.addWidget(btn)
            wrap = QWidget()
            wrap.setLayout(fila)
            self._doc_layout.addWidget(wrap)
        self._doc_layout.addStretch()

    def _adjuntar_documento(self, campo: str):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Adjuntar documento",
            str(Path.home()),
            "Todos (*.*)",
        )
        if not ruta:
            return
        row = self._row()
        dest = self._copiar_doc(row["codigo"], ruta)
        payload = self._payload_equipo(row)
        payload[campo] = dest
        self.db.actualizar_equipo(self.equipo_id, payload)
        self._pintar_documentos(self._row())

    def _payload_equipo(self, row):
        return {
            "codigo": row["codigo"],
            "nombre": row["nombre"],
            "tipo": row["tipo"],
            "marca": row["marca"],
            "modelo": row["modelo"],
            "anio": row["anio"],
            "serie": row["serie"],
            "fabricante": row["fabricante"],
            "motor": row["motor"],
            "serie_motor": row["serie_motor"],
            "potencia": row["potencia"],
            "proyecto": row["proyecto"],
            "ubicacion": row["ubicacion"],
            "estado": row["estado"],
            "observaciones": row["observaciones"],
            "ruta_foto": row["ruta_foto"] or "",
            "ruta_manual": row["ruta_manual"] or "",
            "ruta_manual_partes": row["ruta_manual_partes"] or "",
            "ruta_plano_hidraulico": (
                row["ruta_plano_hidraulico"]
                if "ruta_plano_hidraulico" in row.keys() else ""
            ),
            "ruta_plano_electrico": (
                row["ruta_plano_electrico"]
                if "ruta_plano_electrico" in row.keys() else ""
            ),
        }

    def _copiar_doc(self, codigo: str, origen: str) -> str:
        p = Path(origen)
        dest = ASSETS_EQUIPOS / codigo / "documentos" / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        return str(dest)

    def _tab_fotografias(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        barra = QHBoxLayout()
        self.combo_cat_foto = QComboBox()
        self.combo_cat_foto.addItems(CATEGORIAS_FOTO)
        btn_add = QPushButton("➕ Agregar imagen")
        btn_add.clicked.connect(self._agregar_foto)
        barra.addWidget(QLabel("Categoría:"))
        barra.addWidget(self.combo_cat_foto)
        barra.addWidget(btn_add)
        barra.addStretch()
        layout.addLayout(barra)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.galeria_contenedor = QWidget()
        self.galeria_grid = QGridLayout(self.galeria_contenedor)
        scroll.setWidget(self.galeria_contenedor)
        layout.addWidget(scroll)
        self._cargar_galeria()
        return w

    def _cargar_galeria(self):
        while self.galeria_grid.count():
            item = self.galeria_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fotos = self.db.obtener_fotografias_equipo(self.equipo_id)
        col, row_i = 0, 0
        for foto in fotos:
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.StyledPanel)
            vl = QVBoxLayout(frame)
            vl.addWidget(
            QLabel(f"<b>{foto['categoria']}</b>")
        )
            lbl = MiniaturaFoto(foto["ruta"])
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip("Doble clic para ampliar")
            if Path(foto["ruta"]).is_file():
                pix = QPixmap(foto["ruta"])
                if not pix.isNull():
                    lbl.setPixmap(
                        pix.scaled(
                            140, 105,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            else:
                lbl.setText("No encontrada")
            vl.addWidget(lbl)
            btn_del = QPushButton("Eliminar")
            fid = foto["id"]
            btn_del.clicked.connect(
                lambda _=False, i=fid: self._eliminar_foto(i)
            )
            vl.addWidget(btn_del)
            self.galeria_grid.addWidget(frame, row_i, col)
            col += 1
            if col >= 4:
                col = 0
                row_i += 1

        if not fotos:
            self.galeria_grid.addWidget(
                QLabel("Sin imágenes. Doble clic en miniatura para ampliar."),
                0, 0,
            )

    def _agregar_foto(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Agregar fotografía",
            str(Path.home()),
            "Imágenes (*.png *.jpg *.jpeg *.bmp)",
        )
        if not ruta:
            return
        row = self._row()
        p = Path(ruta)
        dest = ASSETS_EQUIPOS / row["codigo"] / "fotos" / p.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        self.db.agregar_fotografia_equipo(
            self.equipo_id,
            self.combo_cat_foto.currentText(),
            str(dest),
        )
        self._cargar_galeria()

    def _eliminar_foto(self, foto_id: int):
        ok = QMessageBox.question(
            self,
            "Eliminar",
            "¿Eliminar esta imagen de la galería?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        self.db.eliminar_fotografia_equipo(foto_id)
        self._cargar_galeria()

    def _abrir_archivo(self, ruta: str):
        path = Path(ruta)
        if not path.is_file():
            QMessageBox.warning(self, "Documento", "Archivo no encontrado.")
            return
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def _ver_mantenimientos(self):
        QMessageBox.information(
            self,
            "Mantenimientos",
            "Módulo en desarrollo.",
        )

    def _exportar_pdf(self):
        exportar_ficha_pdf(self.db, self.equipo_id, self)

    def _editar_equipo(self):
        dlg = EquipoForm(self, equipo_id=self.equipo_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refrescar_vista()
