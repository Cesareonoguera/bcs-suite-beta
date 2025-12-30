# bcs_4d.py
from fpdf import FPDF
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import statistics
import ifcopenshell.util.element 

# --- CONFIGURACIÓN ---
import os
# Esto obtiene la ruta exacta donde está guardado este archivo .py
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
# Esto combina esa ruta con el nombre del logo
ARCHIVO_LOGO = os.path.join(CARPETA_ACTUAL, "logo.jpg")

# Debug: Imprimir dónde está buscando para que lo veas en la consola
print(f"🔍 Buscando logo en: {ARCHIVO_LOGO}")

ARCHIVO_GANTT = "gantt_temp.png"
UMBRAL_VIGAS_POR_NIVEL = 8
TOLERANCIA_AGRUPACION_MM = 400.0
UMBRAL_PESO_PILAR_KG = 160.0 

def consolidar_por_conjuntos(datos_brutos):
    """
    Agrupa piezas usando 'assembly_mark' para el cálculo.
    """
    print("🧩 4D: Reagrupando por ASSEMBLY MARK...")
    grupos = {}
    
    for item in datos_brutos:
        if item.get("es_tornillo", False) or item["categoria"] == "TORNILLERIA": continue
        
        ref_conjunto = item.get("assembly_mark", "S/R")
        
        if ref_conjunto not in grupos:
            grupos[ref_conjunto] = {
                "peso_total": 0.0, 
                "partes": [],  # Aquí guardamos las piezas originales
                "z_min": 99999.0
            }
        
        grupos[ref_conjunto]["peso_total"] += item["peso_kg"]
        grupos[ref_conjunto]["partes"].append(item)
        z = item.get("altura_z", 0.0)
        if z < grupos[ref_conjunto]["z_min"]: grupos[ref_conjunto]["z_min"] = z
    
    datos_consolidados = []
    for ref, g in grupos.items():
        g["partes"].sort(key=lambda x: x["peso_kg"], reverse=True)
        maestro = g["partes"][0]
        
        datos_consolidados.append({
            "referencia": ref,
            "perfil_maestro": maestro["perfil_maestro"],
            "categoria": maestro["categoria"],
            "peso_kg": g["peso_total"],
            "altura_z": g["z_min"],
            "objeto_ifc": maestro["objeto_ifc"],
            "items_originales": g["partes"], # <--- CLAVE: Guardamos referencia a los originales
            "es_tornillo": False,
            "bcs_fase": "" 
        })
        
    print(f"   -> {len(datos_brutos)} partes reducidas a -> {len(datos_consolidados)} conjuntos.")
    return datos_consolidados

def obtener_desnivel_geometrico(item):
    if "objeto_ifc" not in item: return 0.0
    elemento = item["objeto_ifc"]
    psets = ifcopenshell.util.element.get_psets(elemento)
    bottom = None; top = None
    for ps in psets.values():
        for k, v in ps.items():
            k_low = k.lower()
            if "bottom elevation" in k_low: 
                try: bottom = float(str(v).replace('+', ''))
                except: pass
            if "top elevation" in k_low: 
                try: top = float(str(v).replace('+', ''))
                except: pass
    if bottom is not None and top is not None:
        if abs(top) < 200: top *= 1000.0
        if abs(bottom) < 200: bottom *= 1000.0
        return abs(top - bottom)
    return 0.0

def es_vertical_geometrico(item):
    peso = item.get("peso_kg", 0.0)
    if peso < UMBRAL_PESO_PILAR_KG: return False
    nombre = str(item.get("perfil_maestro", "")).upper()
    es_perfil_pesado = any(x in nombre for x in ["HEA", "HEB", "HEM", "HD", "SHS", "RHS", "TUB", "IPE", "UPN", "W"])
    if not es_perfil_pesado: return False 
    desnivel = obtener_desnivel_geometrico(item)
    if desnivel > 1800.0: return True
    return False

def detectar_niveles_maestros(datos):
    alturas = []
    for item in datos:
        if not es_vertical_geometrico(item): alturas.append(item["altura_z"])
    if not alturas: return [0.0]
    alturas.sort()
    niveles = []; actual = [alturas[0]]
    for z in alturas[1:]:
        if z - actual[-1] < TOLERANCIA_AGRUPACION_MM: actual.append(z)
        else:
            if len(actual) >= UMBRAL_VIGAS_POR_NIVEL: niveles.append(statistics.mean(actual))
            actual = [z]
    if len(actual) >= UMBRAL_VIGAS_POR_NIVEL: niveles.append(statistics.mean(actual))
    if not niveles: return [statistics.mean(alturas)]
    return niveles

def calcular_fechas_para_ifc(datos_brutos, fecha_inicio_obra, rendimiento_kg_dia):
    # 1. Agrupar
    datos_proc = consolidar_por_conjuntos(datos_brutos)
    # 2. Niveles
    niveles = detectar_niveles_maestros(datos_proc)
    
    def nivel_cercano(z): return min(niveles, key=lambda x: abs(x - z))
    
    validos = []
    for item in datos_proc:
        es_col = es_vertical_geometrico(item)
        z = item["altura_z"]
        
        if es_col: z_nivel = round(z/1000.0)*1000.0 
        else: z_nivel = nivel_cercano(z)            
        
        tipo = "PILARES" if es_col else "VIGAS"
        item["bcs_fase"] = f"NIVEL +{z_nivel/1000.0:.2f}m | {tipo}"
        item["_sort_z"] = z_nivel
        item["_sort_tipo"] = "01" if es_col else "02" 
        validos.append(item)
        
    ordenados = sorted(validos, key=lambda x: (x["_sort_z"], x["_sort_tipo"], -x["peso_kg"]))
    
    # 3. Asignar Fechas
    cursor = fecha_inicio_obra
    acum = 0.0
    for item in ordenados:
        p = item["peso_kg"]
        if acum + p <= rendimiento_kg_dia: acum += p
        else:
            cursor += datetime.timedelta(days=1)
            if cursor.weekday() >= 5: cursor += datetime.timedelta(days=(7-cursor.weekday()))
            acum = p
        item["bcs_fecha_plan"] = cursor
        
        # --- PROPAGACIÓN INVERSA (NUEVO) ---
        # Pasamos la fecha calculada para el CONJUNTO a todas las PIEZAS ORIGINALES
        # para que el Injector las encuentre después.
        if "items_originales" in item:
            for pieza in item["items_originales"]:
                pieza["bcs_fecha_plan"] = cursor
                pieza["bcs_fase"] = item["bcs_fase"]

    return ordenados

def generar_imagen_gantt(datos, rendimiento_tn):
    print("📊 4D: Dibujando Gantt...")
    fechas_fases = {}
    fases_ordenadas = [] 
    datos_dibujo = sorted([d for d in datos if "bcs_fase" in d], key=lambda x: (x["_sort_z"], x["_sort_tipo"]))
    for item in datos_dibujo:
        fase = item["bcs_fase"]
        if fase not in fechas_fases: 
            fechas_fases[fase] = []
            if fase not in fases_ordenadas: fases_ordenadas.append(fase)
        fechas_fases[fase].append(item["bcs_fecha_plan"])
    if not fases_ordenadas: return 1.0
    
    num_barras = len(fases_ordenadas)
    ancho_fig = 10.0; altura_fig = max(4.0, num_barras * 0.5 + 2.0)
    if altura_fig > 15.0: altura_fig = 15.0 
    
    fig, ax = plt.subplots(figsize=(ancho_fig, altura_fig))
    y_pos = 0; etiquetas = []; colores = {"PILARES": "#8B4513", "VIGAS": "#4682B4"} 
    
    for fase in fases_ordenadas:
        fechas = sorted(fechas_fases[fase])
        inicio = fechas[0]; fin = fechas[-1]
        duracion = (fin - inicio).days + 1
        tipo = "PILARES" if "PILARES" in fase else "VIGAS"
        color = colores.get(tipo, "#555555")
        ax.barh(y_pos, duracion, left=inicio, height=0.6, align='center', color=color, alpha=0.9, edgecolor='black')
        etiquetas.append(fase)
        ax.text(inicio, y_pos + 0.35, f"{inicio.strftime('%d/%m')}", fontsize=8)
        if duracion > 3: ax.text(fin, y_pos + 0.35, f"{fin.strftime('%d/%m')}", fontsize=8)
        y_pos += 1
    
    ax.set_yticks(range(len(etiquetas))); ax.set_yticklabels(etiquetas)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_title(f"CRONOGRAMA DE MONTAJE ({rendimiento_tn} Tn/día)")
    plt.tight_layout(); plt.savefig(ARCHIVO_GANTT, dpi=100); plt.close()
    return ancho_fig / altura_fig

class InformePlanificacion(FPDF):
    def header(self):
        if self.page_no() == 1: return
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'PLANIFICACIÓN DE OBRA (BIM 4D)', 0, 1, 'L')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'BIM CONSULTING SOLUTIONS SL', 0, 1, 'L')
        self.line(10, 32, 200, 32); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pag {self.page_no()}', 0, 0, 'C')
    def crear_portada(self, ratio_imagen, rendimiento):
        self.add_page()
        if os.path.exists(ARCHIVO_LOGO): self.image(ARCHIVO_LOGO, x=65, y=30, w=80)
        self.ln(80); self.set_font('Arial', 'B', 24); self.cell(0, 20, "PLANIFICACIÓN 4D", 0, 1, 'C')
        self.set_font('Arial', '', 16); self.cell(0, 10, "SECUENCIA DE MONTAJE", 0, 1, 'C')
        self.ln(10); self.set_font('Arial', 'I', 12); self.cell(0, 10, f"Escenario de montaje: {rendimiento} Tn/dia", 0, 1, 'C')
        if os.path.exists(ARCHIVO_GANTT):
            self.ln(5); ancho_max = 190.0; alto_max = 120.0
            w_final = ancho_max; h_final = w_final / ratio_imagen
            if h_final > alto_max: h_final = alto_max; w_final = h_final * ratio_imagen
            x_centrada = (210 - w_final) / 2
            try: self.image(ARCHIVO_GANTT, x=x_centrada, w=w_final, h=h_final)
            except: pass
    def cabecera_tabla(self):
        self.set_font('Arial', 'B', 8); self.set_fill_color(240, 240, 240)
        self.cell(20, 6, "Fecha", 1, 0, 'C', 1); self.cell(40, 6, "Nivel", 1, 0, 'L', 1)
        self.cell(35, 6, "Ref", 1, 0, 'L', 1); self.cell(75, 6, "Elemento", 1, 0, 'L', 1)
        self.cell(20, 6, "Peso(kg)", 1, 1, 'R', 1)
    def fila_item(self, fecha, fase, ref, desc, peso):
        self.set_font('Arial', '', 7)
        self.cell(20, 6, str(fecha.strftime('%d-%m')), 1, 0, 'C')
        fase_corta = fase.split("|")[0].strip()
        self.cell(40, 6, fase_corta, 1, 0, 'L')
        self.cell(35, 6, str(ref)[:18], 1)
        self.cell(75, 6, str(desc)[:45], 1)
        self.cell(20, 6, f"{peso:.1f}", 1, 1, 'R')

def generar_informe_4d(datos, fecha_inicio_obra, rendimiento_kg, nombre_pdf="BCS_Planificacion.pdf"):
    # 1. Calcular cronograma con lógica de conjuntos
    datos_consolidados = calcular_fechas_para_ifc(datos, fecha_inicio_obra, rendimiento_kg)
    rendimiento_tn = rendimiento_kg / 1000.0
    
    # 2. Generar Gráfico
    ratio = generar_imagen_gantt(datos_consolidados, rendimiento_tn)
    
    # 3. Generar PDF
    print(f"📅 4D: Generando PDF '{nombre_pdf}'..."); pdf = InformePlanificacion()
    pdf.crear_portada(ratio, rendimiento_tn)
    
    # Listado
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, "LISTADO DE MONTAJE DIARIO", 0, 1, 'L')
    pdf.ln(5); pdf.cabecera_tabla()
    
    fecha_actual = None; peso_dia = 0
    for item in datos_consolidados:
        if item["bcs_fecha_plan"] != fecha_actual:
            if fecha_actual is not None:
                 pdf.set_font('Arial', 'B', 7); pdf.set_fill_color(220, 255, 220)
                 pdf.cell(170, 5, f"TOTAL ACERO DIA {fecha_actual.strftime('%d-%m-%Y')}:", 1, 0, 'R', 1)
                 pdf.cell(20, 5, f"{peso_dia:.1f} kg", 1, 1, 'R', 1)
            fecha_actual = item["bcs_fecha_plan"]; peso_dia = 0
            
        desc = item.get("perfil_maestro", "Varios")
        pdf.fila_item(fecha_actual, item["bcs_fase"], item["referencia"], desc, item["peso_kg"])
        peso_dia += item["peso_kg"]
        
    if peso_dia > 0 and fecha_actual:
         pdf.set_font('Arial', 'B', 7); pdf.set_fill_color(220, 255, 220)
         pdf.cell(170, 5, f"TOTAL ACERO DIA {fecha_actual.strftime('%d-%m-%Y')}:", 1, 0, 'R', 1)
         pdf.cell(20, 5, f"{peso_dia:.1f} kg", 1, 1, 'R', 1)

    if os.path.exists(ARCHIVO_GANTT): os.remove(ARCHIVO_GANTT)
    pdf.output(nombre_pdf)
    print("✅ 4D: Informe guardado (Por Conjuntos).")