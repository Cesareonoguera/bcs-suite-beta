# bcs_5d.py
from fpdf import FPDF
import datetime
import os

# --- CONFIGURACIÓN ---
import os
# Esto obtiene la ruta exacta donde está guardado este archivo .py
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
# Esto combina esa ruta con el nombre del logo
ARCHIVO_LOGO = os.path.join(CARPETA_ACTUAL, "logo.jpg")

PRECIO_ACERO = 2.65       # EUR/kg (Laminado)
PRECIO_PLACA = 2.10       # EUR/kg (Placa)
PRECIO_TORNILLERIA = 3.50 # EUR/kg
PRECIO_REJILLA = 2.50     # EUR/kg
PRECIO_GENERICO = 2.00    # EUR/kg

class PresupuestoPDF(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'PRESUPUESTO DE EJECUCIÓN MATERIAL (PEM)', 0, 1, 'L')
        self.line(10, 25, 200, 25); self.ln(5)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'BIM Consulting Solutions SL - Pag {self.page_no()}', 0, 0, 'C')

    def crear_portada(self, imagen=None):
        self.add_page()
        if os.path.exists(ARCHIVO_LOGO):
            self.image(ARCHIVO_LOGO, x=10, y=10, w=60)
        
        self.ln(50)
        if imagen and os.path.exists(imagen):
            self.image(imagen, x=55, y=60, w=100) # Foto del modelo
            self.ln(100)
        else:
            self.ln(20)

        self.set_font('Arial', 'B', 24); self.cell(0, 20, "PRESUPUESTO DE ESTRUCTURA", 0, 1, 'C')
        self.set_font('Arial', '', 14); self.cell(0, 10, "MEDICIONES Y VALORACIÓN (BIM 5D)", 0, 1, 'C')
        self.ln(10)
        self.set_font('Arial', '', 12); self.cell(0, 10, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", 0, 1, 'C')
        self.cell(0, 10, "Normativa de medición: UNE 36080 / RICS NRM2", 0, 1, 'C')

    def cabecera_tabla(self, categoria):
        self.ln(5)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 8, f" CAPITULO: {categoria}", 0, 1, 'L')
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 8)
        self.cell(30, 6, "Referencia", 1, 0, 'L', 1)
        self.cell(70, 6, "Descripcion (Perfil)", 1, 0, 'L', 1)
        self.cell(15, 6, "Uds", 1, 0, 'C', 1)
        self.cell(25, 6, "Peso(kg)", 1, 0, 'R', 1)
        self.cell(25, 6, "Pre.Unit", 1, 0, 'R', 1)
        self.cell(25, 6, "TOTAL", 1, 1, 'R', 1)

    def fila_item(self, ref, desc, uds, peso, precio_u, precio_tot):
        self.set_font('Arial', '', 8)
        self.cell(30, 6, str(ref)[:15], 1)
        self.cell(70, 6, str(desc)[:40], 1)
        self.cell(15, 6, str(uds), 1, 0, 'C')
        self.cell(25, 6, f"{peso:.1f}", 1, 0, 'R')
        self.cell(25, 6, f"{precio_u:.2f}", 1, 0, 'R')
        self.cell(25, 6, f"{precio_tot:.2f}", 1, 1, 'R')

    def imprimir_resumen_legal(self, resumen_capitulos):
        self.add_page()
        self.set_font('Arial', 'B', 14); self.cell(0, 10, "RESUMEN DE PRESUPUESTO", 0, 1, 'L')
        self.ln(5)
        
        # Tabla Resumen
        self.set_fill_color(200, 200, 200)
        self.set_font('Arial', 'B', 10)
        self.cell(140, 8, "CAPÍTULO", 1, 0, 'L', 1)
        self.cell(50, 8, "IMPORTE", 1, 1, 'R', 1)
        
        subtotal = 0.0
        self.set_font('Arial', '', 10)
        for cap, importe in resumen_capitulos.items():
            self.cell(140, 8, f"Estructura Metálica - {cap}", 1, 0, 'L')
            self.cell(50, 8, f"{importe:,.2f} EUR", 1, 1, 'R')
            subtotal += importe
            
        # Totales con IVA
        self.ln(5)
        iva = subtotal * 0.21
        total = subtotal + iva
        
        self.set_font('Arial', 'B', 10)
        self.cell(140, 8, "TOTAL EJECUCIÓN MATERIAL (PEM):", 1, 0, 'R')
        self.cell(50, 8, f"{subtotal:,.2f} EUR", 1, 1, 'R')
        
        self.cell(140, 8, "Gastos Generales y Beneficio Ind. (19%):", 1, 0, 'R')
        gg_bi = subtotal * 0.19
        self.cell(50, 8, f"{gg_bi:,.2f} EUR", 1, 1, 'R')
        
        base_imp = subtotal + gg_bi
        self.set_fill_color(230, 230, 230)
        self.cell(140, 10, "BASE IMPONIBLE:", 1, 0, 'R', 1)
        self.cell(50, 10, f"{base_imp:,.2f} EUR", 1, 1, 'R', 1)
        
        self.cell(140, 10, "I.V.A. (21%):", 1, 0, 'R', 1)
        self.cell(50, 10, f"{base_imp * 0.21:,.2f} EUR", 1, 1, 'R', 1)
        
        self.set_fill_color(44, 62, 80); self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 12)
        self.cell(140, 12, "TOTAL PRESUPUESTO CONTRATA:", 1, 0, 'R', 1)
        self.cell(50, 12, f"{(base_imp * 1.21):,.2f} EUR", 1, 1, 'R', 1)
        self.set_text_color(0, 0, 0)

        # Pliego de Condiciones
        self.ln(15)
        self.set_font('Arial', 'B', 10); self.cell(0, 8, "PLIEGO DE CONDICIONES Y ALCANCE:", 0, 1, 'L')
        self.set_font('Arial', '', 8)
        condiciones = (
            "1. Los precios incluyen: Suministro de material, fabricación en taller, granallado SA 2.5, "
            "imprimación y pintura (80 micras), transporte a obra (radio < 50km) y montaje con medios de elevación.\n"
            "2. Medición realizada sobre modelo IFC (BIM) según peso neto (Kg). No se incluyen mermas ni retales.\n"
        )
        self.multi_cell(0, 5, condiciones)

def calcular_costes_para_ifc(datos):
    """
    Función interna que asegura que cada ítem tenga su precio calculado.
    """
    print("💰 5D: Calculando Costes (Interno)...")
    for item in datos:
        cat = item.get("categoria", "GENERICO")
        precio = PRECIO_GENERICO
        if cat == "LAMINADO": precio = PRECIO_ACERO
        elif cat == "PLACA": precio = PRECIO_PLACA
        elif cat == "TORNILLERIA" or item.get("es_tornillo"): precio = PRECIO_TORNILLERIA
        elif cat == "REJILLA": precio = PRECIO_REJILLA
        
        # AQUÍ SE CREAN LAS CLAVES QUE FALTABAN
        item["bcs_coste_item"] = item["peso_kg"] * precio
        item["bcs_precio_unitario"] = precio

def generar_informe_costes(datos, nombre_pdf, imagen=None):
    # 1. EJECUTAR CÁLCULO PRIMERO (Corrección del error)
    calcular_costes_para_ifc(datos)
    
    print(f"💰 5D: Generando Presupuesto Legal '{nombre_pdf}'...")
    
    # Agrupar datos
    grupos = {}
    resumen_capitulos = {} # Para el cuadro final
    
    for item in datos:
        if item["peso_kg"] <= 0: continue
        cat = item.get("categoria", "GENERICO")
        # Referencia = Tag (pieza suelta)
        clave = (cat, item.get("referencia", "S/R"), item.get("perfil_maestro", "Varios"))
        
        if clave not in grupos:
            grupos[clave] = {"uds": 0, "peso": 0.0, "coste": 0.0, "pu": item["bcs_precio_unitario"]}
        
        grupos[clave]["uds"] += 1
        grupos[clave]["peso"] += item["peso_kg"]
        grupos[clave]["coste"] += item["bcs_coste_item"]
        
        # Acumular para resumen
        resumen_capitulos[cat] = resumen_capitulos.get(cat, 0.0) + item["bcs_coste_item"]

    lista = []
    for (cat, ref, desc), v in grupos.items():
        lista.append({"cat": cat, "ref": ref, "desc": desc, **v})
    lista.sort(key=lambda x: (x["cat"], -x["coste"]))

    # Generar PDF
    pdf = PresupuestoPDF()
    pdf.crear_portada(imagen)
    pdf.add_page()
    
    cat_actual = None
    coste_cat = 0
    
    for item in lista:
        if item["cat"] != cat_actual:
            if cat_actual:
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(165, 8, f"TOTAL {cat_actual}:", 0, 0, 'R')
                pdf.cell(25, 8, f"{coste_cat:.2f}", 1, 1, 'R')
                pdf.ln(5)
            cat_actual = item["cat"]
            pdf.cabecera_tabla(cat_actual)
            coste_cat = 0
        
        pdf.fila_item(item["ref"], item["desc"], item["uds"], item["peso"], item["pu"], item["coste"])
        coste_cat += item["coste"]

    if cat_actual:
        pdf.cell(165, 8, f"TOTAL {cat_actual}:", 0, 0, 'R')
        pdf.cell(25, 8, f"{coste_cat:.2f}", 1, 1, 'R')

    # IMPRIMIR RESUMEN LEGAL AL FINAL
    pdf.imprimir_resumen_legal(resumen_capitulos)
    
    pdf.output(nombre_pdf)
    print("✅ 5D: Presupuesto guardado.")

# --- PUENTE DE COMPATIBILIDAD ---
def generar_presupuesto(datos, nombre_pdf):
    # Redirigimos la llamada antigua a la función nueva
    return generar_informe_costes(datos, nombre_pdf)