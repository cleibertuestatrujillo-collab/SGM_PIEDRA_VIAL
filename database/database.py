import sqlite3
from pathlib import Path


class Database:

    def __init__(self):

        self.db_path = Path(__file__).parent / "sgm.db"

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        self.crear_tablas()

    # ======================================================
    # CREAR TABLAS
    # ======================================================

    def crear_tablas(self):

        self.crear_tabla_usuarios()
        self.crear_tabla_equipos()
        self.crear_tabla_inventario()
        self.crear_tabla_movimientos()
        self.crear_tabla_mantenimientos()

        self.conn.commit()

        self.crear_usuario_admin()
        self.cargar_equipos()

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

            marca TEXT,

            modelo TEXT,

            serie TEXT,

            motor TEXT,

            proyecto TEXT,

            horometro REAL,

            estado TEXT

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

            proveedor TEXT,

            observacion TEXT

        )
        """)

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

            INSERT INTO usuarios
            (
                usuario,
                password,
                nombre,
                cargo
            )

            VALUES
            (
                'admin',
                '1234',
                'Administrador',
                'Administrador'
            )

            """)

            self.conn.commit()

    # ======================================================
    # EQUIPOS INICIALES
    # ======================================================

    def cargar_equipos(self):

        equipos = [

            ("CP001","McCloskey J40 V2","McCloskey","J40 V2","","CAT C7.1","YAULI",0,"OPERATIVO"),

            ("CP002","McCloskey J40 V2","McCloskey","J40 V2","","CAT C7.1","LIVITACA",0,"OPERATIVO"),

            ("CS001","Pegson Maxtrak 1300","Terex Pegson","1300","","CAT C13","",0,"OPERATIVO"),

            ("CS002","Kleemann MCO90i EVO2","Kleemann","MCO90i","","Scania DC09","",0,"OPERATIVO"),

            ("ZV001","McCloskey S190","McCloskey","S190","","CAT","",0,"OPERATIVO"),

            ("CV001","McCloskey V80","McCloskey","V80","","CAT","",0,"OPERATIVO")

        ]

        for equipo in equipos:

            self.cursor.execute(
                "SELECT * FROM equipos WHERE codigo=?",
                (equipo[0],)
            )

            if self.cursor.fetchone() is None:

                self.cursor.execute("""

                INSERT INTO equipos
                (
                    codigo,
                    nombre,
                    marca,
                    modelo,
                    serie,
                    motor,
                    proyecto,
                    horometro,
                    estado
                )

                VALUES
                (?,?,?,?,?,?,?,?,?)

                """, equipo)

        self.conn.commit()


db = Database()