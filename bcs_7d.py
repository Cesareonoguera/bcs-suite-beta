# bcs_7d.py
from fpdf import FPDF
import datetime
import os

# --- CONFIGURACIÓN ---
import os
# Esto obtiene la ruta exacta donde está guardado este archivo .py
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
# Esto combina esa ruta con el nombre del logo
ARCHIVO_LOGO = os.path.join(CARPETA_ACTUAL, "logo.jpg")

NORMATIVA_REF = "Código Estructural (RD 470/2021) / CTE DB-SE-A"
VIDA_UTIL_PROYECTO = 50 # Años

# --- OPERACIONES DE MANTENIMIENTO ESTÁNDAR (CTE/EAE) ---
OPERACIONES = [
    {"op": "Inspección Visual General", "freq": "Anual", "desc": "Detectar golpes, deformaciones o humedades."},
    {"op": "Revisión Pintura/Galvanizado", "freq": "Cada 5 años", "desc": "Verificar óxido, descascarillado (cat. C3/C4)."},
    {"op": "Reapriete de Pernos", "freq": "1er año / Cada 5", "desc": "Comprobar par de apriete en uniones atornilladas."},
    {"op": "Limpieza de Elementos", "freq": "Según necesidad", "desc": "Evitar acumulación de suciedad/sales en rincones."},
    {"op": "Inspección Soldaduras", "freq": "Cada 10 años", "desc": "Revisión visual de cordones principales (fisuras)."}
]

def consolidar_inventario(datos_brutos):
    """
    Agrupa elementos sueltos en Conjuntos (Assemblies) para el inventario de mantenimiento.
    """
    print("🛠️ 7D: Agrupando inventario para Mantenimiento...")
    grupos = {}
    for item in datos_brutos:
        # Ignorar tornillería suelta en el listado principal de equipos
        if item.get("es_tornillo", False) or item["categoria"] == "TORNILLERIA": continue
        
        # Agrupar por Assembly Mark (Marca de Conjunto)
        ref_conjunto = item.get("assembly_mark", "S/R")
        
        if ref_conjunto not in grupos:
            grupos[ref_conjunto] = {
                "nombre": item.get("perfil_maestro", "Elemento Estructural"),
                "peso": 0.0,
                "uds": 0,
                "zona": item.get("nivel", "General") 
            }
        
        grupos[ref_conjunto]["peso"] += item["peso_kg"]
        # Contamos la pieza maestra como unidad representativa
        if item["objeto_ifc"] == item.get("perfil_maestro_obj"): 
             grupos[ref_conjunto]["uds"] += 1
             
    # Ajuste de seguridad por si no cuenta bien las unidades
    for k, v in grupos.items():
        if v["uds"] == 0: v["uds"] = 1

    lista = []
    for ref, datos in grupos.items():
        lista.append({"ref": ref, **datos})
    
    lista.sort(key=lambda x: x["ref"])
    return lista

class ManualMantenimiento(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'MANUAL DE USO Y MANTENIMIENTO (BIM 7D)', 0, 1, 'L')
        self.line(10, 20, 200, 20); self.ln(10)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'BIM Consulting Solutions - Pag {self.page_no()}', 0, 0, 'C')

    def crear_portada(self, imagen=None):
        self.add_page()
        if os.path.exists(ARCHIVO_LOGO): self.image(ARCHIVO_LOGO, x=75, y=30, w=60)
        self.ln(60)
        
        self.set_font('Arial', 'B', 22); self.cell(0, 15, "LIBRO DE MANTENIMIENTO", 0, 1, 'C')
        self.set_font('Arial', '', 14); self.cell(0, 10, "ESTRUCTURA METÁLICA", 0, 1, 'C')
        self.ln(10)
        
        # Cuadro Normativa
        self.set_fill_color(240, 240, 240); self.set_draw_color(100, 100, 100)
        self.rect(40, 140, 130, 40, 'DF')
        self.set_y(145)
        self.set_font('Arial', 'B', 10); self.cell(0, 5, "MARCO NORMATIVO DE REFERENCIA:", 0, 1, 'C')
        self.ln(2)
        self.set_font('Arial', '', 9)
        self.cell(0, 5, NORMATIVA_REF, 0, 1, 'C')
        self.cell(0, 5, "Ley de Ordenación de la Edificación (LOE)", 0, 1, 'C')
        self.cell(0, 5, f"Vida Útil de Diseño: {VIDA_UTIL_PROYECTO} años", 0, 1, 'C')

    def tabla_operaciones(self):
        self.add_page()
        self.set_font('Arial', 'B', 14); self.cell(0, 10, "1. PROGRAMA DE MANTENIMIENTO PREVENTIVO", 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, "De acuerdo al Art. 25 del Código Estructural, se establece el siguiente calendario de operaciones mínimas para garantizar la durabilidad.")
        self.ln(5)
        
        # Cabecera
        self.set_fill_color(50, 50, 100); self.set_text_color(255, 255, 255); self.set_font('Arial', 'B', 10)
        self.cell(60, 8, "OPERACIÓN", 1, 0, 'C', 1)
        self.cell(30, 8, "FRECUENCIA", 1, 0, 'C', 1)
        self.cell(100, 8, "DESCRIPCIÓN / CRITERIO DE ACEPTACIÓN", 1, 1, 'C', 1)
        
        self.set_text_color(0, 0, 0); self.set_font('Arial', '', 9)
        fill = False
        for op in OPERACIONES:
            fill = not fill
            if fill: self.set_fill_color(230, 230, 245)
            else: self.set_fill_color(255, 255, 255)
            
            self.cell(60, 8, op["op"], 1, 0, 'L', 1)
            self.cell(30, 8, op["freq"], 1, 0, 'C', 1)
            self.cell(100, 8, op["desc"], 1, 1, 'L', 1)

    def tabla_inventario(self, inventario):
        self.add_page()
        self.set_font('Arial', 'B', 14); self.cell(0, 10, "2. INVENTARIO DE ELEMENTOS MANTENIBLES", 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, "Listado consolidado de conjuntos estructurales (Assemblies). No incluye despiece de taller.")
        self.ln(5)
        
        # Cabecera
        self.set_fill_color(100, 100, 100); self.set_text_color(255, 255, 255); self.set_font('Arial', 'B', 9)
        self.cell(30, 7, "REF. CONJ.", 1, 0, 'C', 1)
        self.cell(80, 7, "DESCRIPCIÓN TIPO", 1, 0, 'L', 1)
        self.cell(30, 7, "UBICACIÓN", 1, 0, 'C', 1)
        self.cell(20, 7, "UDS", 1, 0, 'C', 1)
        self.cell(30, 7, "PESO (Kg)", 1, 1, 'R', 1)
        
        self.set_text_color(0, 0, 0); self.set_font('Arial', '', 8)
        total_peso = 0
        fill = False
        
        for item in inventario:
            fill = not fill
            color = 240 if fill else 255
            self.set_fill_color(color, color, color)
            
            self.cell(30, 6, str(item["ref"]), 1, 0, 'C', 1)
            self.cell(80, 6, str(item["nombre"])[:45], 1, 0, 'L', 1)
            self.cell(30, 6, str(item["zona"]), 1, 0, 'C', 1)
            self.cell(20, 6, str(item["uds"]), 1, 0, 'C', 1)
            self.cell(30, 6, f"{item['peso']:.1f}", 1, 1, 'R', 1)
            total_peso += item["peso"]
            
        self.set_font('Arial', 'B', 9)
        self.cell(160, 8, "PESO TOTAL MANTENIBLE:", 1, 0, 'R')
        self.cell(30, 8, f"{total_peso:.1f} kg", 1, 1, 'R')

    def ficha_seguridad(self):
        self.add_page()
        self.set_font('Arial', 'B', 14); self.cell(0, 10, "3. LIMITACIONES DE USO Y SEGURIDAD", 0, 1, 'L')
        self.ln(5)
        self.set_font('Arial', '', 10)
        points = [
            "PROHIBICIÓN de realizar taladros o soldaduras no previstas en proyecto.",
            "CARGAS MÁXIMAS: No superar las sobrecargas de uso indicadas en planos.",
            "FUEGO: En caso de incendio, la estructura debe ser inspeccionada por técnico competente.",
            "MODIFICACIONES: Cualquier cambio de uso requiere recálculo estructural."
        ]
        for p in points:
            self.cell(5, 5, "-", 0, 0)
            self.multi_cell(0, 5, p)
            self.ln(2)

# CAMBIO: Renombrado para que coincida con tu llamada en main
def generar_informe_7d(datos, nombre_pdf, imagen=None):
    print(f"🛠️ 7D: Generando Manual '{nombre_pdf}'...")
    
    # 1. Consolidar datos (Parts -> Assemblies)
    inventario = consolidar_inventario(datos)
    
    # 2. Generar PDF
    pdf = ManualMantenimiento()
    pdf.crear_portada(imagen)
    pdf.tabla_operaciones()
    pdf.tabla_inventario(inventario)
    pdf.ficha_seguridad()
    
    pdf.output(nombre_pdf)
    print("✅ 7D: Manual de Mantenimiento guardado.")