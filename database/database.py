import sqlite3
from datetime import datetime
from pathlib import Path


def normalizar_moneda(moneda) -> str:
    if moneda is None or str(moneda).strip() == "":
        return "USD"
    m = str(moneda).strip().upper()
    if m in ("PEN", "S/", "SOLES"):
        return "PEN"
    return "USD"


def formatear_precio_inventario(precio, moneda=None) -> str:
    try:
        valor = float(precio if precio is not None else 0)
    except (TypeError, ValueError):
        valor = 0.0
    texto = f"{valor:.2f}"
    if normalizar_moneda(moneda) == "PEN":
        return f"S/ {texto}"
    return f"$ {texto}"


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_ready", False):
            return
        self._ready = True

        self.db_path = Path(__file__).parent / "sgm.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.crear_tablas()

    # ======================================================
    # CREAR TABLAS
    # ======================================================

    def crear_tablas(self):
        self.crear_tabla_usuarios()
        self.crear_tabla_equipos()
        self.crear_tabla_equipo_horometro()
        self.crear_tabla_equipo_inventario()
        self.crear_tabla_equipo_fotografias()
        self.crear_tabla_equipo_inspecciones()
        self.crear_tabla_inventario()
        self.crear_tabla_movimientos()
        self.crear_tabla_mantenimientos()
        self.crear_tabla_lotes()
        self.crear_tabla_kardex()

        self.conn.commit()

        self.crear_usuario_admin()
        self.cargar_equipos()
        self._migrar_lotes_desde_inventario()
        self._migrar_mantenimientos_equipo_id()
        self._migrar_horometro_historial_desde_equipos()
        self._migrar_fotos_legacy()

    # ======================================================
    # USUARIOS
    # ======================================================

    def crear_tabla_usuarios(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            password TEXT,
            nombre TEXT,
            cargo TEXT,
            estado INTEGER DEFAULT 1
        )
        """)

    # ======================================================
    # EQUIPOS
    # ======================================================

    def crear_tabla_equipos(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            nombre TEXT,
            tipo TEXT,
            marca TEXT,
            modelo TEXT,
            anio TEXT,
            serie TEXT,
            fabricante TEXT,
            motor TEXT,
            serie_motor TEXT,
            potencia TEXT,
            proyecto TEXT,
            ubicacion TEXT,
            horometro REAL DEFAULT 0,
            estado TEXT DEFAULT 'Operativo',
            observaciones TEXT,
            ruta_foto TEXT,
            ruta_manual TEXT,
            ruta_manual_partes TEXT,
            ruta_plano_hidraulico TEXT,
            ruta_plano_electrico TEXT,
            costo_repuestos REAL DEFAULT 0,
            costo_mano_obra REAL DEFAULT 0,
            costo_total REAL DEFAULT 0
        )
        """)
        self._migrar_equipos()

    def _migrar_equipos(self):
        self.cursor.execute("PRAGMA table_info(equipos)")
        columnas = {fila[1] for fila in self.cursor.fetchall()}
        nuevas = {
            "tipo": "TEXT",
            "anio": "TEXT",
            "fabricante": "TEXT",
            "serie_motor": "TEXT",
            "potencia": "TEXT",
            "ubicacion": "TEXT",
            "observaciones": "TEXT",
            "ruta_foto": "TEXT",
            "ruta_manual": "TEXT",
            "ruta_manual_partes": "TEXT",
            "ruta_plano_hidraulico": "TEXT",
            "ruta_plano_electrico": "TEXT",
            "costo_repuestos": "REAL DEFAULT 0",
            "costo_mano_obra": "REAL DEFAULT 0",
            "costo_total": "REAL DEFAULT 0",
        }
        for nombre, tipo_sql in nuevas.items():
            if nombre not in columnas:
                self.cursor.execute(
                    f"ALTER TABLE equipos ADD COLUMN {nombre} {tipo_sql}"
                )
        self.conn.commit()
        self._normalizar_estados_equipos_legacy()

    def _normalizar_estados_equipos_legacy(self):
        mapa = {
            "OPERATIVO": "Operativo",
            "MANTENIMIENTO": "En mantenimiento",
            "PARADA": "Fuera de servicio",
            "BAJA": "Fuera de servicio",
        }
        for antiguo, nuevo in mapa.items():
            self.cursor.execute(
                "UPDATE equipos SET estado = ? WHERE estado = ?",
                (nuevo, antiguo),
            )
        self.conn.commit()

    def _migrar_horometro_historial_desde_equipos(self):
        """Si hay horómetro en equipos sin historial, crea la primera lectura."""
        self._migrar_equipo_horometro_usuario()
        self.cursor.execute("""
            SELECT id, horometro FROM equipos
            WHERE horometro IS NOT NULL AND horometro > 0
        """)
        for row in self.cursor.fetchall():
            self.cursor.execute(
                "SELECT COUNT(*) FROM equipo_horometro WHERE equipo_id = ?",
                (row["id"],),
            )
            if self.cursor.fetchone()[0] == 0:
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute("""
                    INSERT INTO equipo_horometro
                    (equipo_id, fecha, horometro, usuario, observacion)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row["id"],
                    fecha,
                    row["horometro"],
                    "sistema",
                    "Migración desde campo horómetro del equipo",
                ))
        self.conn.commit()

    def _migrar_fotos_legacy(self):
        """Mueve ruta_foto de equipos a equipo_fotografias si aplica."""
        self.cursor.execute("""
            SELECT id, ruta_foto FROM equipos
            WHERE ruta_foto IS NOT NULL AND ruta_foto != ''
        """)
        for row in self.cursor.fetchall():
            self.cursor.execute(
                "SELECT COUNT(*) FROM equipo_fotografias WHERE equipo_id = ?",
                (row["id"],),
            )
            if self.cursor.fetchone()[0] > 0:
                continue
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO equipo_fotografias
                (equipo_id, categoria, ruta, fecha, observacion)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["id"],
                "Equipo",
                row["ruta_foto"],
                fecha,
                "Migración desde ruta_foto",
            ))
        self.conn.commit()

    def _migrar_mantenimientos_equipo_id(self):
        self.cursor.execute("PRAGMA table_info(mantenimientos)")
        columnas = {fila[1] for fila in self.cursor.fetchall()}
        if "equipo_id" not in columnas:
            self.cursor.execute("""
                ALTER TABLE mantenimientos
                ADD COLUMN equipo_id INTEGER REFERENCES equipos(id)
            """)
            self.conn.commit()
            self.cursor.execute("""
                UPDATE mantenimientos
                SET equipo_id = (
                    SELECT id FROM equipos
                    WHERE equipos.codigo = mantenimientos.equipo
                       OR equipos.nombre = mantenimientos.equipo
                    LIMIT 1
                )
                WHERE equipo_id IS NULL AND equipo IS NOT NULL AND equipo != ''
            """)
            self.conn.commit()

    def crear_tabla_equipo_horometro(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipo_horometro(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            horometro REAL NOT NULL,
            usuario TEXT,
            observacion TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
        """)
        self._migrar_equipo_horometro_usuario()

    def _migrar_equipo_horometro_usuario(self):
        self.cursor.execute("PRAGMA table_info(equipo_horometro)")
        columnas = {fila[1] for fila in self.cursor.fetchall()}
        if "usuario" not in columnas:
            self.cursor.execute(
                "ALTER TABLE equipo_horometro ADD COLUMN usuario TEXT"
            )
            self.conn.commit()

    def crear_tabla_equipo_fotografias(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipo_fotografias(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            ruta TEXT NOT NULL,
            fecha TEXT,
            observacion TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
        """)

    def crear_tabla_equipo_inspecciones(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipo_inspecciones(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            fecha TEXT,
            tipo TEXT,
            resultado TEXT,
            observacion TEXT,
            usuario TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
        """)
        self._migrar_equipo_inspecciones()

    def _migrar_equipo_inspecciones(self):
        self.cursor.execute("PRAGMA table_info(equipo_inspecciones)")
        columnas = {fila[1] for fila in self.cursor.fetchall()}
        nuevas = {
            "tipo": "TEXT",
            "resultado": "TEXT",
            "observacion": "TEXT",
            "usuario": "TEXT",
        }
        for nombre, tipo_sql in nuevas.items():
            if nombre not in columnas:
                self.cursor.execute(
                    f"ALTER TABLE equipo_inspecciones ADD COLUMN {nombre} {tipo_sql}"
                )
        self.conn.commit()
        self.cursor.execute("PRAGMA table_info(equipo_inspecciones)")
        columnas = {fila[1] for fila in self.cursor.fetchall()}
        if "tipo_checklist" in columnas:
            self.cursor.execute("""
                UPDATE equipo_inspecciones SET
                    tipo = COALESCE(NULLIF(tipo, ''), tipo_checklist),
                    resultado = COALESCE(NULLIF(resultado, ''), estado),
                    observacion = COALESCE(NULLIF(observacion, ''), observaciones),
                    usuario = COALESCE(NULLIF(usuario, ''), responsable)
            """)
            self.conn.commit()

    def crear_tabla_equipo_inventario(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipo_inventario(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            inventario_id INTEGER NOT NULL,
            notas TEXT,
            UNIQUE(equipo_id, inventario_id),
            FOREIGN KEY (equipo_id) REFERENCES equipos(id),
            FOREIGN KEY (inventario_id) REFERENCES inventario(id)
        )
        """)

    # ======================================================
    # INVENTARIO
    # ======================================================

    def crear_tabla_inventario(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            descripcion TEXT,
            numero_parte TEXT,
            marca TEXT,
            equipo TEXT,
            sistema TEXT,
            categoria TEXT,
            ubicacion TEXT,
            stock REAL,
            stock_min REAL,
            unidad TEXT,
            precio REAL,
            moneda TEXT DEFAULT 'USD',
            proveedor TEXT,
            observacion TEXT
        )
        """)
        self._migrar_inventario_moneda()

    def _migrar_inventario_moneda(self):
        self.cursor.execute("PRAGMA table_info(inventario)")
        columnas = [fila[1] for fila in self.cursor.fetchall()]
        if "moneda" not in columnas:
            self.cursor.execute("""
                ALTER TABLE inventario
                ADD COLUMN moneda TEXT DEFAULT 'USD'
            """)
            self.conn.commit()

    # ======================================================
    # MOVIMIENTOS
    # ======================================================

    def crear_tabla_movimientos(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            codigo TEXT,
            descripcion TEXT,
            tipo TEXT,
            cantidad REAL,
            observacion TEXT
        )
        """)

    # ======================================================
    # LOTES (PEPS / FIFO)
    # ======================================================

    def crear_tabla_lotes(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            fecha_entrada TEXT NOT NULL,
            cantidad_inicial REAL NOT NULL,
            cantidad_restante REAL NOT NULL,
            costo_unitario REAL NOT NULL,
            moneda TEXT DEFAULT 'USD',
            documento TEXT,
            observacion TEXT,
            kardex_id INTEGER,
            FOREIGN KEY (inventario_id) REFERENCES inventario(id)
        )
        """)

    # ======================================================
    # KARDEX
    # ======================================================

    def crear_tabla_kardex(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS kardex(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            inventario_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            descripcion TEXT,
            tipo TEXT NOT NULL,
            cantidad REAL NOT NULL,
            costo_unitario REAL NOT NULL,
            costo_total REAL NOT NULL,
            saldo_cantidad REAL NOT NULL,
            costo_promedio REAL NOT NULL,
            moneda TEXT DEFAULT 'USD',
            documento TEXT,
            observacion TEXT,
            FOREIGN KEY (inventario_id) REFERENCES inventario(id)
        )
        """)

    # ======================================================
    # MANTENIMIENTOS
    # ======================================================

    def crear_tabla_mantenimientos(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo TEXT,
            fecha TEXT,
            horometro REAL,
            tipo TEXT,
            descripcion TEXT,
            costo REAL,
            responsable TEXT
        )
        """)

    # ======================================================
    # USUARIO ADMIN
    # ======================================================

    def crear_usuario_admin(self):
        self.cursor.execute(
            "SELECT * FROM usuarios WHERE usuario='admin'"
        )

        if self.cursor.fetchone() is None:
            self.cursor.execute("""
            INSERT INTO usuarios (usuario, password, nombre, cargo)
            VALUES ('admin', '1234', 'Administrador', 'Administrador')
            """)
            self.conn.commit()

    # ======================================================
    # EQUIPOS INICIALES
    # ======================================================

    def cargar_equipos(self):
        equipos = [
            (
                "CP001", "McCloskey J40 V2", "Chancadora Primaria", "McCloskey",
                "J40 V2", "", "", "McCloskey", "CAT C7.1", "", "", "YAULI",
                "YAULI", 0, "Operativo", "", "", "", "", "", "", 0, 0, 0,
            ),
            (
                "CP002", "McCloskey J40 V2", "Chancadora Primaria", "McCloskey",
                "J40 V2", "", "", "McCloskey", "CAT C7.1", "", "", "LIVITACA",
                "LIVITACA", 0, "Operativo", "", "", "", "", "", "", 0, 0, 0,
            ),
            (
                "CS001", "Pegson Maxtrak 1300", "Chancadora Secundaria",
                "Terex Pegson", "1300", "", "", "Terex", "CAT C13", "", "",
                "", "", 0, "Operativo", "", "", "", "", "", "", 0, 0, 0,
            ),
            (
                "CS002", "Kleemann MCO90i EVO2", "Chancadora Secundaria",
                "Kleemann", "MCO90i", "", "", "Kleemann", "Scania DC09", "", "",
                "", "", 0, "Operativo", "", "", "", "", "", "", 0, 0, 0,
            ),
            (
                "ZV001", "McCloskey S190", "Zaranda", "McCloskey", "S190", "",
                "", "McCloskey", "CAT", "", "", "", "", 0, "Operativo",
                "", "", "", "", "", "", 0, 0, 0,
            ),
            (
                "CV001", "McCloskey V80", "Chancadora Terciaria", "McCloskey",
                "V80", "", "", "McCloskey", "CAT", "", "", "", "", 0,
                "Operativo", "", "", "", "", "", "", 0, 0, 0,
            ),
        ]

        for eq in equipos:
            self.cursor.execute(
                "SELECT id FROM equipos WHERE codigo=?",
                (eq[0],),
            )
            if self.cursor.fetchone() is None:
                self.cursor.execute("""
                INSERT INTO equipos (
                    codigo, nombre, tipo, marca, modelo, anio, serie,
                    fabricante, motor, serie_motor, potencia, proyecto,
                    ubicacion, horometro, estado, observaciones,
                    ruta_foto, ruta_manual, ruta_manual_partes,
                    ruta_plano_hidraulico, ruta_plano_electrico,
                    costo_repuestos, costo_mano_obra, costo_total
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, eq)

        self.conn.commit()

    # ======================================================
    # INVENTARIO — CONSULTAS Y CRUD
    # ======================================================

    _SQL_INVENTARIO_LIST = """
        SELECT
            id,
            codigo,
            descripcion,
            numero_parte,
            marca,
            equipo,
            categoria,
            ubicacion,
            stock,
            stock_min,
            unidad,
            precio,
            moneda,
            proveedor
        FROM inventario
    """

    def obtener_repuestos(self):
        self.cursor.execute(
            self._SQL_INVENTARIO_LIST + " ORDER BY descripcion"
        )
        return self.cursor.fetchall()

    def buscar_repuestos(self, termino: str):
        termino = termino.strip()
        if not termino:
            return self.obtener_repuestos()

        like = f"%{termino}%"
        self.cursor.execute(
            self._SQL_INVENTARIO_LIST + """
            WHERE
                codigo LIKE ?
                OR descripcion LIKE ?
                OR numero_parte LIKE ?
                OR marca LIKE ?
                OR equipo LIKE ?
                OR categoria LIKE ?
                OR ubicacion LIKE ?
                OR proveedor LIKE ?
            ORDER BY descripcion
            """,
            (like, like, like, like, like, like, like, like),
        )
        return self.cursor.fetchall()

    def obtener_repuesto_por_id(self, repuesto_id: int):
        self.cursor.execute(
            "SELECT * FROM inventario WHERE id = ?",
            (repuesto_id,),
        )
        return self.cursor.fetchone()

    def insertar_repuesto(self, datos: dict):
        self.cursor.execute("""
            INSERT INTO inventario (
                codigo, descripcion, numero_parte, marca, equipo, sistema,
                categoria, ubicacion, stock, stock_min, unidad, precio,
                moneda, proveedor, observacion
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datos["codigo"],
            datos["descripcion"],
            datos.get("numero_parte") or "",
            datos.get("marca") or "",
            datos.get("equipo") or "",
            datos.get("sistema") or "",
            datos.get("categoria") or "",
            datos.get("ubicacion") or "",
            datos["stock"],
            datos["stock_min"],
            datos.get("unidad") or "UND",
            datos["precio"],
            normalizar_moneda(datos.get("moneda")),
            datos.get("proveedor") or "",
            datos.get("observacion") or "",
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def actualizar_repuesto(self, repuesto_id: int, datos: dict):
        self.cursor.execute("""
            UPDATE inventario SET
                codigo = ?,
                descripcion = ?,
                numero_parte = ?,
                marca = ?,
                equipo = ?,
                sistema = ?,
                categoria = ?,
                ubicacion = ?,
                stock = ?,
                stock_min = ?,
                unidad = ?,
                precio = ?,
                moneda = ?,
                proveedor = ?,
                observacion = ?
            WHERE id = ?
        """, (
            datos["codigo"],
            datos["descripcion"],
            datos.get("numero_parte") or "",
            datos.get("marca") or "",
            datos.get("equipo") or "",
            datos.get("sistema") or "",
            datos.get("categoria") or "",
            datos.get("ubicacion") or "",
            datos["stock"],
            datos["stock_min"],
            datos.get("unidad") or "UND",
            datos["precio"],
            normalizar_moneda(datos.get("moneda")),
            datos.get("proveedor") or "",
            datos.get("observacion") or "",
            repuesto_id,
        ))
        self.conn.commit()

    def eliminar_repuesto(self, repuesto_id: int):
        self.cursor.execute(
            "DELETE FROM inventario WHERE id = ?",
            (repuesto_id,),
        )
        self.conn.commit()

    # ======================================================
    # KARDEX / LOTES — PEPS (FIFO)
    # ======================================================

    def _migrar_lotes_desde_inventario(self):
        self.cursor.execute("""
            SELECT id, codigo, stock, precio, moneda
            FROM inventario
            WHERE COALESCE(stock, 0) > 0
        """)
        repuestos = self.cursor.fetchall()
        for rep in repuestos:
            self.cursor.execute(
                "SELECT COUNT(*) AS n FROM lotes WHERE inventario_id = ?",
                (rep["id"],),
            )
            if self.cursor.fetchone()["n"] > 0:
                continue
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            moneda = normalizar_moneda(
                rep["moneda"] if "moneda" in rep.keys() else "USD"
            )
            precio = float(rep["precio"] or 0)
            stock = float(rep["stock"] or 0)
            self.cursor.execute("""
                INSERT INTO lotes (
                    inventario_id, codigo, fecha_entrada,
                    cantidad_inicial, cantidad_restante,
                    costo_unitario, moneda, documento, observacion
                ) VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                rep["id"],
                rep["codigo"],
                fecha,
                stock,
                stock,
                precio,
                moneda,
                "SALDO-INICIAL",
                "Lote generado desde stock existente en inventario",
            ))
        self.conn.commit()

    def asegurar_lotes_inventario(self, inventario_id: int):
        rep = self.obtener_repuesto_por_id(inventario_id)
        if rep is None:
            return
        stock = float(rep["stock"] or 0)
        if stock <= 0:
            return
        self.cursor.execute(
            "SELECT COUNT(*) AS n FROM lotes WHERE inventario_id = ?",
            (inventario_id,),
        )
        if self.cursor.fetchone()["n"] > 0:
            return
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        moneda = normalizar_moneda(
            rep["moneda"] if "moneda" in rep.keys() else "USD"
        )
        precio = float(rep["precio"] or 0)
        self.cursor.execute("""
            INSERT INTO lotes (
                inventario_id, codigo, fecha_entrada,
                cantidad_inicial, cantidad_restante,
                costo_unitario, moneda, documento, observacion
            ) VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            inventario_id,
            rep["codigo"],
            fecha,
            stock,
            stock,
            precio,
            moneda,
            "SALDO-INICIAL",
            "Lote generado desde stock en inventario",
        ))
        self.conn.commit()

    def _costo_promedio_lotes(self, inventario_id: int) -> float:
        self.cursor.execute("""
            SELECT
                COALESCE(SUM(cantidad_restante * costo_unitario), 0) AS valor,
                COALESCE(SUM(cantidad_restante), 0) AS cantidad
            FROM lotes
            WHERE inventario_id = ? AND cantidad_restante > 0
        """, (inventario_id,))
        row = self.cursor.fetchone()
        cantidad = float(row["cantidad"] or 0)
        if cantidad <= 0:
            return 0.0
        return float(row["valor"]) / cantidad

    def _stock_lotes(self, inventario_id: int) -> float:
        self.cursor.execute("""
            SELECT COALESCE(SUM(cantidad_restante), 0) AS total
            FROM lotes WHERE inventario_id = ?
        """, (inventario_id,))
        return float(self.cursor.fetchone()["total"] or 0)

    def obtener_resumen_kardex(self, inventario_id: int) -> dict:
        self.asegurar_lotes_inventario(inventario_id)
        rep = self.obtener_repuesto_por_id(inventario_id)
        if rep is None:
            return {
                "stock_actual": 0.0,
                "costo_promedio": 0.0,
                "saldo": 0.0,
                "moneda": "USD",
            }
        stock_lotes = self._stock_lotes(inventario_id)
        stock_inv = float(rep["stock"] or 0)
        stock_actual = stock_lotes if stock_lotes > 0 else stock_inv
        costo_prom = self._costo_promedio_lotes(inventario_id)
        if costo_prom == 0 and stock_actual > 0:
            costo_prom = float(rep["precio"] or 0)
        moneda = normalizar_moneda(
            rep["moneda"] if "moneda" in rep.keys() else "USD"
        )
        self.cursor.execute("""
            SELECT saldo_cantidad FROM kardex
            WHERE inventario_id = ?
            ORDER BY id DESC LIMIT 1
        """, (inventario_id,))
        ultimo = self.cursor.fetchone()
        saldo = (
            float(ultimo["saldo_cantidad"])
            if ultimo is not None
            else stock_actual
        )
        return {
            "stock_actual": stock_actual,
            "costo_promedio": costo_prom,
            "saldo": saldo,
            "moneda": moneda,
            "codigo": rep["codigo"],
            "descripcion": rep["descripcion"],
        }

    def obtener_movimientos_kardex(self, inventario_id: int):
        self.cursor.execute("""
            SELECT *
            FROM kardex
            WHERE inventario_id = ?
            ORDER BY fecha ASC, id ASC
        """, (inventario_id,))
        return self.cursor.fetchall()

    def registrar_entrada_kardex(
        self,
        inventario_id: int,
        cantidad: float,
        costo_unitario: float,
        moneda: str = "USD",
        documento: str = "",
        observacion: str = "",
        fecha: str | None = None,
    ) -> int:
        from datetime import datetime

        if cantidad <= 0:
            raise ValueError("La cantidad de entrada debe ser mayor a cero.")
        if costo_unitario < 0:
            raise ValueError("El costo unitario no puede ser negativo.")

        rep = self.obtener_repuesto_por_id(inventario_id)
        if rep is None:
            raise ValueError("Repuesto no encontrado en inventario.")

        moneda = normalizar_moneda(moneda)
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        stock_prev = float(rep["stock"] or 0)
        saldo = stock_prev + cantidad
        costo_total = cantidad * costo_unitario

        try:
            self.cursor.execute("""
                INSERT INTO kardex (
                    fecha, inventario_id, codigo, descripcion, tipo,
                    cantidad, costo_unitario, costo_total,
                    saldo_cantidad, costo_promedio, moneda,
                    documento, observacion
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                fecha,
                inventario_id,
                rep["codigo"],
                rep["descripcion"],
                "ENTRADA",
                cantidad,
                costo_unitario,
                costo_total,
                saldo,
                0.0,
                moneda,
                documento or "",
                observacion or "",
            ))
            kardex_id = self.cursor.lastrowid

            self.cursor.execute("""
                INSERT INTO lotes (
                    inventario_id, codigo, fecha_entrada,
                    cantidad_inicial, cantidad_restante,
                    costo_unitario, moneda, documento, observacion, kardex_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                inventario_id,
                rep["codigo"],
                fecha,
                cantidad,
                cantidad,
                costo_unitario,
                moneda,
                documento or "",
                observacion or "",
                kardex_id,
            ))

            costo_prom = self._costo_promedio_lotes(inventario_id)
            self.cursor.execute(
                "UPDATE kardex SET costo_promedio = ? WHERE id = ?",
                (costo_prom, kardex_id),
            )

            self.cursor.execute(
                "UPDATE inventario SET stock = ? WHERE id = ?",
                (saldo, inventario_id),
            )

            self.conn.commit()
            return kardex_id
        except Exception:
            self.conn.rollback()
            raise

    def registrar_salida_kardex(
        self,
        inventario_id: int,
        cantidad: float,
        documento: str = "",
        observacion: str = "",
        fecha: str | None = None,
    ) -> int:
        if cantidad <= 0:
            raise ValueError("La cantidad de salida debe ser mayor a cero.")

        rep = self.obtener_repuesto_por_id(inventario_id)
        if rep is None:
            raise ValueError("Repuesto no encontrado en inventario.")

        stock_disp = self._stock_lotes(inventario_id)
        if stock_disp < cantidad:
            raise ValueError(
                f"Stock insuficiente en lotes. Disponible: {stock_disp:.2f}, "
                f"solicitado: {cantidad:.2f}."
            )

        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        moneda = normalizar_moneda(
            rep["moneda"] if "moneda" in rep.keys() else "USD"
        )

        try:
            pendiente = cantidad
            costo_total_salida = 0.0

            self.cursor.execute("""
                SELECT id, cantidad_restante, costo_unitario
                FROM lotes
                WHERE inventario_id = ? AND cantidad_restante > 0
                ORDER BY fecha_entrada ASC, id ASC
            """, (inventario_id,))
            lotes = self.cursor.fetchall()

            for lote in lotes:
                if pendiente <= 0:
                    break
                rest = float(lote["cantidad_restante"])
                tomar = min(rest, pendiente)
                costo_total_salida += tomar * float(lote["costo_unitario"])
                nuevo_rest = rest - tomar
                self.cursor.execute(
                    "UPDATE lotes SET cantidad_restante = ? WHERE id = ?",
                    (nuevo_rest, lote["id"]),
                )
                pendiente -= tomar

            if pendiente > 0.0001:
                raise ValueError("No fue posible consumir lotes (PEPS).")

            costo_unit_salida = costo_total_salida / cantidad
            stock_prev = float(rep["stock"] or 0)
            saldo = stock_prev - cantidad
            if saldo < 0:
                raise ValueError("La salida dejaría stock negativo.")

            costo_prom = self._costo_promedio_lotes(inventario_id)

            self.cursor.execute("""
                INSERT INTO kardex (
                    fecha, inventario_id, codigo, descripcion, tipo,
                    cantidad, costo_unitario, costo_total,
                    saldo_cantidad, costo_promedio, moneda,
                    documento, observacion
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                fecha,
                inventario_id,
                rep["codigo"],
                rep["descripcion"],
                "SALIDA",
                cantidad,
                costo_unit_salida,
                costo_total_salida,
                saldo,
                costo_prom,
                moneda,
                documento or "",
                observacion or "",
            ))
            kardex_id = self.cursor.lastrowid

            self.cursor.execute(
                "UPDATE inventario SET stock = ? WHERE id = ?",
                (saldo, inventario_id),
            )

            self.conn.commit()
            return kardex_id
        except Exception:
            self.conn.rollback()
            raise

    # ======================================================
    # EQUIPOS — CONSULTAS Y CRUD
    # ======================================================

    _SQL_EQUIPOS_LIST = """
        SELECT
            id, codigo, nombre, tipo, marca, modelo, anio, serie,
            fabricante, motor, serie_motor, potencia, proyecto, ubicacion,
            horometro, estado, observaciones, ruta_foto, ruta_manual,
            ruta_manual_partes, ruta_plano_hidraulico, ruta_plano_electrico,
            costo_repuestos, costo_mano_obra, costo_total
        FROM equipos
    """

    def obtener_horometro_actual(self, equipo_id: int) -> float:
        self.cursor.execute("""
            SELECT horometro FROM equipo_horometro
            WHERE equipo_id = ?
            ORDER BY fecha DESC, id DESC
            LIMIT 1
        """, (equipo_id,))
        row = self.cursor.fetchone()
        if row is not None:
            return float(row["horometro"])
        self.cursor.execute(
            "SELECT horometro FROM equipos WHERE id = ?",
            (equipo_id,),
        )
        eq = self.cursor.fetchone()
        if eq and eq["horometro"] is not None:
            return float(eq["horometro"])
        return 0.0

    def obtener_equipos(self):
        self.cursor.execute(
            self._SQL_EQUIPOS_LIST + " ORDER BY codigo"
        )
        return self.cursor.fetchall()

    def buscar_equipos(self, termino: str):
        termino = termino.strip()
        if not termino:
            return self.obtener_equipos()
        like = f"%{termino}%"
        self.cursor.execute(
            self._SQL_EQUIPOS_LIST + """
            WHERE
                codigo LIKE ? OR nombre LIKE ? OR tipo LIKE ?
                OR marca LIKE ? OR modelo LIKE ? OR proyecto LIKE ?
                OR ubicacion LIKE ? OR estado LIKE ? OR motor LIKE ?
            ORDER BY codigo
            """,
            (like,) * 9,
        )
        return self.cursor.fetchall()

    def obtener_equipo_por_id(self, equipo_id: int):
        self.cursor.execute(
            "SELECT * FROM equipos WHERE id = ?",
            (equipo_id,),
        )
        return self.cursor.fetchone()

    def insertar_equipo(self, datos: dict):
        self.cursor.execute("""
            INSERT INTO equipos (
                codigo, nombre, tipo, marca, modelo, anio, serie, fabricante,
                motor, serie_motor, potencia, proyecto, ubicacion, horometro,
                estado, observaciones, ruta_foto, ruta_manual, ruta_manual_partes,
                ruta_plano_hidraulico, ruta_plano_electrico,
                costo_repuestos, costo_mano_obra, costo_total
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, self._tupla_equipo(datos, incluir_horometro=True))
        self.conn.commit()
        equipo_id = self.cursor.lastrowid
        self._sync_mantenimientos_equipo_id(equipo_id, datos.get("codigo"))
        return equipo_id

    def actualizar_equipo(self, equipo_id: int, datos: dict):
        self.cursor.execute("""
            UPDATE equipos SET
                codigo = ?, nombre = ?, tipo = ?, marca = ?, modelo = ?,
                anio = ?, serie = ?, fabricante = ?, motor = ?, serie_motor = ?,
                potencia = ?, proyecto = ?, ubicacion = ?,
                estado = ?, observaciones = ?, ruta_foto = ?, ruta_manual = ?,
                ruta_manual_partes = ?, ruta_plano_hidraulico = ?,
                ruta_plano_electrico = ?
            WHERE id = ?
        """, self._tupla_equipo(datos, incluir_horometro=False) + (equipo_id,))
        self.conn.commit()
        self._sync_mantenimientos_equipo_id(equipo_id, datos.get("codigo"))

    def eliminar_equipo(self, equipo_id: int):
        self.cursor.execute(
            "DELETE FROM equipo_horometro WHERE equipo_id = ?",
            (equipo_id,),
        )
        self.cursor.execute(
            "DELETE FROM equipo_fotografias WHERE equipo_id = ?",
            (equipo_id,),
        )
        self.cursor.execute(
            "DELETE FROM equipo_inspecciones WHERE equipo_id = ?",
            (equipo_id,),
        )
        self.cursor.execute(
            "DELETE FROM equipo_inventario WHERE equipo_id = ?",
            (equipo_id,),
        )
        self.cursor.execute(
            "DELETE FROM equipos WHERE id = ?",
            (equipo_id,),
        )
        self.conn.commit()

    def _tupla_equipo(self, datos: dict, incluir_horometro: bool = True):
        base = (
            datos["codigo"],
            datos["nombre"],
            datos.get("tipo") or "",
            datos.get("marca") or "",
            datos.get("modelo") or "",
            datos.get("anio") or "",
            datos.get("serie") or "",
            datos.get("fabricante") or "",
            datos.get("motor") or "",
            datos.get("serie_motor") or "",
            datos.get("potencia") or "",
            datos.get("proyecto") or "",
            datos.get("ubicacion") or "",
        )
        if incluir_horometro:
            base += (
                0.0,
                datos.get("estado") or "Operativo",
                datos.get("observaciones") or "",
                datos.get("ruta_foto") or "",
                datos.get("ruta_manual") or "",
                datos.get("ruta_manual_partes") or "",
                datos.get("ruta_plano_hidraulico") or "",
                datos.get("ruta_plano_electrico") or "",
                float(datos.get("costo_repuestos") or 0),
                float(datos.get("costo_mano_obra") or 0),
                float(datos.get("costo_total") or 0),
            )
        else:
            base += (
                datos.get("estado") or "Operativo",
                datos.get("observaciones") or "",
                datos.get("ruta_foto") or "",
                datos.get("ruta_manual") or "",
                datos.get("ruta_manual_partes") or "",
                datos.get("ruta_plano_hidraulico") or "",
                datos.get("ruta_plano_electrico") or "",
            )
        return base

    def _sync_mantenimientos_equipo_id(self, equipo_id: int, codigo: str):
        if not codigo:
            return
        row = self.obtener_equipo_por_id(equipo_id)
        if row is None:
            return
        self.cursor.execute("""
            UPDATE mantenimientos
            SET equipo_id = ?
            WHERE equipo_id IS NULL
              AND (equipo = ? OR equipo = ?)
        """, (equipo_id, codigo, row["nombre"] or ""))
        self.conn.commit()

    def registrar_horometro_equipo(
        self,
        equipo_id: int,
        horometro: float,
        observacion: str = "",
        usuario: str = "",
    ):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO equipo_horometro
            (equipo_id, fecha, horometro, usuario, observacion)
            VALUES (?, ?, ?, ?, ?)
        """, (
            equipo_id,
            fecha,
            horometro,
            usuario or "admin",
            observacion or "",
        ))
        self.conn.commit()

    def obtener_historial_horometro(self, equipo_id: int):
        self.cursor.execute("""
            SELECT id, fecha, horometro, usuario, observacion
            FROM equipo_horometro
            WHERE equipo_id = ?
            ORDER BY fecha DESC, id DESC
        """, (equipo_id,))
        return self.cursor.fetchall()

    def agregar_fotografia_equipo(
        self,
        equipo_id: int,
        categoria: str,
        ruta: str,
        observacion: str = "",
    ):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO equipo_fotografias
            (equipo_id, categoria, ruta, fecha, observacion)
            VALUES (?, ?, ?, ?, ?)
        """, (equipo_id, categoria, ruta, fecha, observacion or ""))
        self.conn.commit()
        return self.cursor.lastrowid

    def obtener_fotografias_equipo(self, equipo_id: int):
        self.cursor.execute("""
            SELECT id, categoria, ruta, fecha, observacion
            FROM equipo_fotografias
            WHERE equipo_id = ?
            ORDER BY categoria, fecha DESC
        """, (equipo_id,))
        return self.cursor.fetchall()

    def eliminar_fotografia_equipo(self, foto_id: int):
        self.cursor.execute(
            "DELETE FROM equipo_fotografias WHERE id = ?",
            (foto_id,),
        )
        self.conn.commit()

    def obtener_inspecciones_equipo(self, equipo_id: int):
        self.cursor.execute("""
            SELECT
                id,
                equipo_id,
                fecha,
                COALESCE(tipo, tipo_checklist, '') AS tipo,
                COALESCE(resultado, estado, '') AS resultado,
                COALESCE(observacion, observaciones, '') AS observacion,
                COALESCE(usuario, responsable, '') AS usuario
            FROM equipo_inspecciones
            WHERE equipo_id = ?
            ORDER BY fecha DESC, id DESC
        """, (equipo_id,))
        return self.cursor.fetchall()

    def obtener_repuestos_compatibles_equipo(self, equipo_id: int):
        row = self.obtener_equipo_por_id(equipo_id)
        if row is None:
            return []
        self.cursor.execute("""
            SELECT
                i.id, i.codigo, i.descripcion, i.numero_parte, i.stock,
                i.unidad, ei.notas
            FROM equipo_inventario ei
            INNER JOIN inventario i ON i.id = ei.inventario_id
            WHERE ei.equipo_id = ?
            ORDER BY i.descripcion
        """, (equipo_id,))
        vinculados = self.cursor.fetchall()
        if vinculados:
            return vinculados
        nombre = row["nombre"] or ""
        codigo = row["codigo"] or ""
        like_n = f"%{nombre}%"
        like_c = f"%{codigo}%"
        self.cursor.execute("""
            SELECT id, codigo, descripcion, numero_parte, stock, unidad, '' AS notas
            FROM inventario
            WHERE equipo LIKE ? OR equipo LIKE ? OR descripcion LIKE ?
            ORDER BY descripcion
        """, (like_n, like_c, like_n))
        return self.cursor.fetchall()

    def obtener_mantenimientos_equipo(self, equipo_id: int):
        row = self.obtener_equipo_por_id(equipo_id)
        if row is None:
            return []
        self.cursor.execute("""
            SELECT id, fecha, horometro, tipo, descripcion, costo, responsable
            FROM mantenimientos
            WHERE equipo_id = ?
               OR equipo = ?
               OR equipo = ?
            ORDER BY fecha DESC
        """, (equipo_id, row["codigo"] or "", row["nombre"] or ""))
        return self.cursor.fetchall()

    def vincular_repuesto_equipo(
        self, equipo_id: int, inventario_id: int, notas: str = ""
    ):
        self.cursor.execute("""
            INSERT OR IGNORE INTO equipo_inventario (equipo_id, inventario_id, notas)
            VALUES (?, ?, ?)
        """, (equipo_id, inventario_id, notas or ""))
        self.conn.commit()


def get_database() -> Database:
    return Database()
