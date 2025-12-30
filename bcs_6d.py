# bcs_6d.py
from fpdf import FPDF
import datetime
import os

# --- CONFIGURACIÓN ---
import os
# Esto obtiene la ruta exacta donde está guardado este archivo .py
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
# Esto combina esa ruta con el nombre del logo
ARCHIVO_LOGO = os.path.join(CARPETA_ACTUAL, "logo.jpg")

# --- FACTORES DE IMPACTO FIJOS (Estables - Fuente: BEDEC/OECC) ---
FACTORES_IMPACTO = {
    "LAMINADO": 1.85, 
    "PLACA": 2.45,    
    "TORNILLERIA": 0.0, 
    "GENERICO": 1.50, 
    "REJILLA": 2.10   
}

class InformeHuella(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_font('Arial', 'B', 10)
        self.set_text_color(34, 139, 34)
        self.cell(0, 10, 'DECLARACION AMBIENTAL DE PRODUCTO (SIMPLIFICADA)', 0, 1, 'L')
        self.set_text_color(0, 0, 0); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Norma ISO 14064 / ISO 14025', 0, 1, 'R')
        
        self.set_draw_color(34, 139, 34)
        self.line(10, 32, 200, 32) 
        self.set_draw_color(0, 0, 0)
        self.ln(5)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 7)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'Factores de emision: Base de Datos BEDEC (ITeC) - Alcance A1-A3 (Cuna a Puerta)', 0, 0, 'C')

    def crear_portada(self, total_co2, ratio, imagen=None):
        self.add_page()
        if os.path.exists(ARCHIVO_LOGO):
            self.image(ARCHIVO_LOGO, x=75, y=30, w=60)
        
        self.ln(50)
        if imagen and os.path.exists(imagen):
            self.image(imagen, x=55, y=60, w=100)
            self.ln(100)
        else:
            self.ln(20)

        self.set_text_color(34, 139, 34)
        self.set_font('Arial', 'B', 24); self.cell(0, 20, "INFORME DE HUELLA DE CARBONO", 0, 1, 'C')
        
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, "DIMENSION BIM: 6D (SOSTENIBILIDAD)", 0, 1, 'C')
        
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 14); self.cell(0, 10, "ANALISIS DE CICLO DE VIDA (Fase Producto A1-A3)", 0, 1, 'C')
        self.ln(10)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", 0, 1, 'C')
        self.cell(0, 10, "Referencia: ISO 14067 (Huella de Carbono de Productos)", 0, 1, 'C')

        self.ln(15)
        self.set_fill_color(235, 250, 235); self.set_draw_color(34, 139, 34)
        self.rect(50, 230, 110, 30, 'FD')
        self.set_y(235); self.set_font('Arial', 'B', 10); self.set_text_color(34, 139, 34)
        self.cell(0, 5, "OBJETIVO DEL INFORME:", 0, 1, 'C')
        self.set_font('Arial', '', 9); self.set_text_color(0,0,0)
        self.cell(0, 5, "Cuantificacion de emisiones de Gases de Efecto Invernadero (GEI)", 0, 1, 'C')
        self.cell(0, 5, "asociadas a la fabricacion de la estructura metalica.", 0, 1, 'C')

    def cabecera_tabla(self, categoria):
        self.ln(8)
        self.set_font('Arial', 'B', 11); self.set_text_color(0,0,0)
        self.cell(0, 8, f" CATEGORIA: {categoria}", 0, 1, 'L')
        self.set_fill_color(34, 139, 34); self.set_text_color(255,255,255); self.set_font('Arial', 'B', 8)
        self.cell(30, 7, "Referencia", 1, 0, 'L', 1)
        self.cell(70, 7, "Descripcion", 1, 0, 'L', 1)
        self.cell(15, 7, "Uds", 1, 0, 'C', 1)
        self.cell(25, 7, "Peso(kg)", 1, 0, 'R', 1)
        self.cell(25, 7, "Factor", 1, 0, 'C', 1)
        self.cell(25, 7, "kgCO2eq", 1, 1, 'R', 1)
        self.set_text_color(0, 0, 0)

    def fila_item(self, ref, desc, uds, peso_tot, factor, co2, color_fondo):
        self.set_font('Arial', '', 8)
        if color_fondo: self.set_fill_color(235, 250, 235) 
        else: self.set_fill_color(255, 255, 255)
        self.cell(30, 6, str(ref)[:15], 1, 0, 'L', 1)
        self.cell(70, 6, str(desc)[:40], 1, 0, 'L', 1)
        self.cell(15, 6, str(uds), 1, 0, 'C', 1)
        self.cell(25, 6, f"{peso_tot:.1f}", 1, 0, 'R', 1)
        self.cell(25, 6, f"{factor:.2f}", 1, 0, 'C', 1)
        self.cell(25, 6, f"{co2:.2f}", 1, 1, 'R', 1)

    def imprimir_veredicto(self, total_co2, ratio):
        self.ln(10)
        self.set_fill_color(200, 230, 200); self.set_draw_color(34, 139, 34)
        self.rect(15, self.get_y(), 180, 25, 'FD')
        self.ln(5); self.set_font('Arial', 'B', 12); self.set_text_color(0, 100, 0)
        self.cell(0, 8, "DICTAMEN AMBIENTAL", 0, 1, 'C')
        self.set_font('Arial', '', 10); self.set_text_color(0, 0, 0)
        texto = f"Huella Total: {total_co2:.2f} tCO2eq  |  Intensidad: {ratio:.2f} kgCO2/kg acero"
        self.cell(0, 8, texto, 0, 1, 'C')
        self.ln(10)

def calcular_huella_para_ifc(datos):
    """
    Función interna que asegura que cada ítem tenga su huella calculada.
    """
    print("🌍 6D: Calculando Huella de Carbono (Interno)...")
    for item in datos:
        cat_original = item.get("categoria", "GENERICO")
        
        # Detectar placas y asignar factor correcto
        es_placa = False
        perfil = str(item.get("perfil_maestro", "")).upper()
        if "PL" in perfil or "PLATE" in perfil or "CHAPA" in perfil or "FLAT" in perfil: es_placa = True
        
        if es_placa: cat_6d = "PLACA"
        elif item.get("es_tornillo") or cat_original == "TORNILLERIA": cat_6d = "TORNILLERIA"
        else: cat_6d = cat_original

        factor = FACTORES_IMPACTO.get(cat_6d, 1.50)
        
        # ¡AQUÍ ES DONDE SE CREAN LAS CLAVES QUE DABAN ERROR!
        item["_bcs_cat_6d"] = cat_6d
        item["bcs_factor_impacto"] = factor
        item["bcs_huella_item"] = item["peso_kg"] * factor

def generar_informe_sostenibilidad(datos, nombre_pdf, imagen=None):
    # 1. EJECUTAR CÁLCULO PRIMERO (Corrección del error)
    calcular_huella_para_ifc(datos)
    
    print(f"🌍 6D: Generando PDF '{nombre_pdf}'...")
    
    # 2. Agrupar datos ya calculados
    grupos = {}
    for item in datos:
        # Ahora sí existe 'bcs_factor_impacto' porque ejecutamos el paso 1
        if item.get("bcs_factor_impacto", 0) <= 0: continue
        
        clave = (item.get("_bcs_cat_6d", "GENERICO"), item.get("referencia", "S/R"), item.get("perfil_maestro", "Varios"))
        
        if clave not in grupos: 
            grupos[clave] = {"uds": 0, "peso": 0.0, "co2": 0.0, "factor": item["bcs_factor_impacto"]}
            
        grupos[clave]["uds"] += 1
        grupos[clave]["peso"] += item["peso_kg"]
        grupos[clave]["co2"] += item["bcs_huella_item"]

    # 3. Ordenar y preparar lista
    lista = []
    for (cat, ref, desc), v in grupos.items():
        lista.append({"cat": cat, "ref": ref, "desc": desc, **v})
    lista.sort(key=lambda x: (x["cat"], -x["co2"]))

    # 4. Totales
    total_co2_tn = sum(x["co2"] for x in lista) / 1000.0 
    peso_total_kg = sum(x["peso"] for x in lista)
    ratio = (total_co2_tn * 1000) / peso_total_kg if peso_total_kg > 0 else 0

    # 5. Generar PDF
    pdf = InformeHuella()
    pdf.crear_portada(total_co2_tn, ratio, imagen)
    pdf.add_page()
    
    cat_actual = None; co2_cat = 0; alternar = False
    for item in lista:
        if item["cat"] != cat_actual:
            if cat_actual: 
                pdf.cell(165, 8, f"TOTAL {cat_actual}:", 0, 0, 'R')
                pdf.cell(25, 8, f"{co2_cat:.2f}", 1, 1, 'R'); pdf.ln(2)
            cat_actual = item["cat"]; pdf.cabecera_tabla(cat_actual); co2_cat = 0
        pdf.fila_item(item["ref"], item["desc"], item["uds"], item["peso"], item["factor"], item["co2"], alternar)
        co2_cat += item["co2"]; alternar = not alternar

    if cat_actual:
        pdf.cell(165, 8, f"TOTAL {cat_actual}:", 0, 0, 'R'); pdf.cell(25, 8, f"{co2_cat:.2f}", 1, 1, 'R')

    pdf.imprimir_veredicto(total_co2_tn, ratio)
    pdf.output(nombre_pdf)
    print("✅ 6D: Informe ECO guardado.")