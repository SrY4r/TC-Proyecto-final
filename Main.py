import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re
from datetime import datetime

# ==========================================
# MÓDULO 1: BASE DE DATOS (PERSISTENCIA)
# ==========================================
class BaseDatos:
    def __init__(self, db_name="telemetria_puno.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.crear_tablas()

    def crear_tablas(self):
        # Tabla para tramas válidas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                estacion TEXT,
                temperatura REAL,
                bateria TEXT,
                estado TEXT
            )
        ''')
        # Tabla para errores (RNF03)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS errores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                trama_original TEXT,
                tipo_error TEXT,
                detalle TEXT
            )
        ''')
        self.conn.commit()

    def guardar_registro(self, estacion, temp, bat, estado):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO registros (fecha, estacion, temperatura, bateria, estado)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha, estacion, temp, bat, estado))
        self.conn.commit()

    def guardar_error(self, trama, tipo, detalle):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO errores (fecha, trama_original, tipo_error, detalle)
            VALUES (?, ?, ?, ?)
        ''', (fecha, trama, tipo, detalle))
        self.conn.commit()

    def obtener_registros(self):
        self.cursor.execute("SELECT * FROM registros ORDER BY id DESC")
        return self.cursor.fetchall()

    def obtener_errores(self):
        self.cursor.execute("SELECT * FROM errores ORDER BY id DESC")
        return self.cursor.fetchall()


# ==========================================
# MÓDULO 2: ANALIZADOR LÉXICO (AFD)
# ==========================================
class AnalizadorLexico:
    def tokenizar(self, trama):
        trama_limpia = trama.replace(" ", "")
        tokens = []
        
        # Expresiones regulares alineadas al documento
        patrones = [
            ('TK_HEADER', r'^HDR'),
            ('TK_DELIM', r'^#'),
            ('TK_ESTACION', r'^ST[0-9]{2}'),
            ('TK_DELIM', r'^#'),
            ('TK_VAR_TEMP', r'^TMP'),
            ('TK_NUM_REAL', r'^-?[0-9]+\.[0-9]'),
            ('TK_DELIM', r'^#'),
            ('TK_BATERIA', r'^BAT[0-9]{2,3}')
        ]

        posicion = 0
        for tipo, patron in patrones:
            match = re.match(patron, trama_limpia[posicion:])
            if match:
                lexema = match.group(0)
                tokens.append((tipo, lexema))
                posicion += len(lexema)
            else:
                # Si falla un patrón, se detiene y reporta error léxico
                return None, f"Carácter inesperado o formato inválido cerca de: '{trama_limpia[posicion:]}'"

        # Verificar si sobraron caracteres (ruido)
        if posicion < len(trama_limpia):
            return None, f"Caracteres no reconocidos al final de la trama: '{trama_limpia[posicion:]}'"

        return tokens, "Éxito"


# ==========================================
# MÓDULO 3: ANALIZADOR SINTÁCTICO (LR)
# ==========================================
class AnalizadorSintactico:
    def parsear(self, tokens):
        # Simulación de autómata de pila basado en gramática libre de contexto
        # S -> HEADER DELIM ESTACION DELIM VAR_TEMP NUM_REAL DELIM BATERIA
        gramatica_esperada = [
            'TK_HEADER', 'TK_DELIM', 'TK_ESTACION', 'TK_DELIM', 
            'TK_VAR_TEMP', 'TK_NUM_REAL', 'TK_DELIM', 'TK_BATERIA'
        ]
        
        pila = []
        pasos = []
        
        for i, token in enumerate(tokens):
            pila.append(token[0])
            pasos.append(f"Shift: {token[0]} -> Pila: {pila}")
            
            # Verificación de estructura en tiempo real
            if i < len(gramatica_esperada):
                if token[0] != gramatica_esperada[i]:
                    return False, f"Error Sintáctico: Se esperaba {gramatica_esperada[i]}, pero se encontró {token[0]}", pasos
            else:
                return False, "Error Sintáctico: Demasiados tokens en la trama", pasos

        if len(pila) != len(gramatica_esperada):
            return False, "Error Sintáctico: Trama incompleta. Faltan elementos.", pasos

        pasos.append("✅ Reduce: Estructura validada correctamente.")
        return True, "Sintaxis Válida", pasos


# ==========================================
# MÓDULO 4: INTERFAZ GRÁFICA (DASHBOARD)
# ==========================================
class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Alerta Temprana de Heladas - Puno 2026")
        self.root.geometry("900x700")
        self.root.configure(bg="#f8fafc")

        self.db = BaseDatos()
        self.lexer = AnalizadorLexico()
        self.parser = AnalizadorSintactico()

        self.crear_ui()
        self.actualizar_tablas()

    def crear_ui(self):
        # Estilos
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook (Pestañas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # --- Pestaña 1: Monitor en Vivo ---
        self.tab_monitor = tk.Frame(self.notebook, bg="#f8fafc")
        self.notebook.add(self.tab_monitor, text=" 🖥️ Monitor de Recepción ")
        self.setup_tab_monitor()

        # --- Pestaña 2: Base de Datos ---
        self.tab_db = tk.Frame(self.notebook, bg="#f8fafc")
        self.notebook.add(self.tab_db, text=" 🗄️ Base de Datos ")
        self.setup_tab_db()

    def setup_tab_monitor(self):
        # Panel Superior: Entrada
        frame_input = tk.Frame(self.tab_monitor, bg="#f8fafc")
        frame_input.pack(pady=15, padx=20, fill="x")

        tk.Label(frame_input, text="Ingrese Trama Telemática (ASCII):", font=("Arial", 12), bg="#f8fafc").pack(anchor="w")
        
        frame_entry = tk.Frame(frame_input, bg="#f8fafc")
        frame_entry.pack(fill="x", pady=5)
        
        self.entry_trama = tk.Entry(frame_entry, font=("Courier", 14), width=40)
        self.entry_trama.pack(side="left", padx=(0, 10))
        self.entry_trama.insert(0, "HDR#ST01#TMP-05.2#BAT88")

        tk.Button(frame_entry, text="▶ PROCESAR", command=self.procesar_trama, bg="#2563eb", fg="white", font=("Arial", 10, "bold")).pack(side="left")

        # Botones de Prueba Rápida
        frame_btn = tk.Frame(frame_input, bg="#f8fafc")
        frame_btn.pack(pady=5, anchor="w")
        tk.Button(frame_btn, text="Simular Trama Válida (Helada)", command=lambda: self.set_trama("HDR#ST05#TMP-02.1#BAT95"), bg="#bbf7d0").pack(side="left", padx=5)
        tk.Button(frame_btn, text="Simular Trama Válida (Normal)", command=lambda: self.set_trama("HDR#ST02#TMP12.5#BAT80"), bg="#bfdbfe").pack(side="left", padx=5)
        tk.Button(frame_btn, text="Simular Error Léxico (Ruido)", command=lambda: self.set_trama("HDR#ST01#TMP-05.2#BAT88@#!"), bg="#fecaca").pack(side="left", padx=5)
        tk.Button(frame_btn, text="Simular Error Sintáctico", command=lambda: self.set_trama("HDR#ST01#TMP-05.2BAT88"), bg="#fecaca").pack(side="left", padx=5)

        # Panel de Alerta (Visualmente llamativo)
        self.lbl_alerta = tk.Label(self.tab_monitor, text="SISTEMA EN ESPERA...", font=("Arial", 16, "bold"), bg="#94a3b8", fg="white", pady=15)
        self.lbl_alerta.pack(fill="x", padx=20, pady=10)

        # Consola de Log
        tk.Label(self.tab_monitor, text="Trazabilidad del Parser (Log):", font=("Arial", 10, "bold"), bg="#f8fafc").pack(anchor="w", padx=20)
        self.text_log = tk.Text(self.tab_monitor, height=15, font=("Courier", 10), bg="#1e293b", fg="#a7f3d0")
        self.text_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def setup_tab_db(self):
        # Tabla de Registros
        tk.Label(self.tab_db, text="Historial de Telemetría Válida:", font=("Arial", 12, "bold"), bg="#f8fafc").pack(anchor="w", padx=20, pady=10)
        
        columns = ('ID', 'Fecha', 'Estación', 'Temperatura', 'Batería', 'Estado')
        self.tree = ttk.Treeview(self.tab_db, columns=columns, show='headings', height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill="x", padx=20)

        # Tabla de Errores
        tk.Label(self.tab_db, text="Registro de Errores (Logs):", font=("Arial", 12, "bold"), bg="#f8fafc", fg="#dc2626").pack(anchor="w", padx=20, pady=10)
        
        columns_err = ('ID', 'Fecha', 'Trama Original', 'Tipo de Error', 'Detalle')
        self.tree_err = ttk.Treeview(self.tab_db, columns=columns_err, show='headings', height=8)
        for col in columns_err:
            self.tree_err.heading(col, text=col)
            self.tree_err.column(col, width=120)
        self.tree_err.column('Detalle', width=250)
        self.tree_err.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def set_trama(self, trama):
        self.entry_trama.delete(0, tk.END)
        self.entry_trama.insert(0, trama)

    def procesar_trama(self):
        trama = self.entry_trama.get()
        self.text_log.delete(1.0, tk.END)
        self.text_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] RECEPCIÓN: {trama}\n\n")

        # 1. Fase Léxica
        self.text_log.insert(tk.END, "--- EVALUACIÓN LÉXICA (AFD) ---\n")
        tokens, msj_lex = self.lexer.tokenizar(trama)
        if not tokens:
            self.text_log.insert(tk.END, f"❌ {msj_lex}\n")
            self.lbl_alerta.config(text="❌ ERROR LÉXICO: TRAMA DESCARTADA", bg="#ef4444")
            self.db.guardar_error(trama, "Léxico", msj_lex)
            self.actualizar_tablas()
            return

        for t in tokens:
            self.text_log.insert(tk.END, f"  -> Token: {t[0]:<15} | Lexema: {t[1]}\n")
        self.text_log.insert(tk.END, "✅ Léxico OK.\n\n")

        # 2. Fase Sintáctica
        self.text_log.insert(tk.END, "--- EVALUACIÓN SINTÁCTICA (LR) ---\n")
        es_valido, msj_sin, pasos = self.parser.parsear(tokens)
        
        for paso in pasos:
            self.text_log.insert(tk.END, f"  {paso}\n")

        if not es_valido:
            self.text_log.insert(tk.END, f"❌ {msj_sin}\n")
            self.lbl_alerta.config(text="❌ ERROR SINTÁCTICO: TRAMA DESCARTADA", bg="#ef4444")
            self.db.guardar_error(trama, "Sintáctico", msj_sin)
            self.actualizar_tablas()
            return
        self.text_log.insert(tk.END, "✅ Sintaxis OK.\n\n")

        # 3. Fase de Decisión y Persistencia
        self.text_log.insert(tk.END, "--- EVALUACIÓN DE RIESGO ---\n")
        estacion = [t[1] for t in tokens if t[0] == 'TK_ESTACION'][0]
        temp = float([t[1] for t in tokens if t[0] == 'TK_NUM_REAL'][0])
        bateria = [t[1] for t in tokens if t[0] == 'TK_BATERIA'][0]

        self.text_log.insert(tk.END, f"  Estación: {estacion} | Temp: {temp}°C | Bat: {bateria}\n")

        if temp < 0.0:
            self.text_log.insert(tk.END, "⚠️ ALERTA: Temperatura bajo cero detectada.\n")
            self.lbl_alerta.config(text="🚨 ¡ALERTA DE HELADA DISPARADA! (SMS/Sirena)", bg="#dc2626")
            self.db.guardar_registro(estacion, temp, bateria, "ALERTA_HELADA")
            # Simulación de envío de SMS
            messagebox.showwarning("ALERTA CRÍTICA", f"¡HELADA DETECTADA!\nEstación: {estacion}\nTemperatura: {temp}°C\nSe ha enviado una alerta SMS a los agricultores.")
        else:
            self.text_log.insert(tk.END, "📊 Temperatura normal. Registro guardado.\n")
            self.lbl_alerta.config(text="✅ REGISTRO NORMAL GUARDADO EN BD", bg="#10b981")
            self.db.guardar_registro(estacion, temp, bateria, "NORMAL")

        self.actualizar_tablas()

    def actualizar_tablas(self):
        # Limpiar tablas
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in self.tree_err.get_children():
            self.tree_err.delete(row)

        # Cargar datos
        for reg in self.db.obtener_registros():
            self.tree.insert('', tk.END, values=reg)
            
        for err in self.db.obtener_errores():
            self.tree_err.insert('', tk.END, values=err)

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()