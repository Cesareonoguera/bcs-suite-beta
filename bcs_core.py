# bcs_core.py
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import google.generativeai as genai

DENSIDAD_ACERO = 7850.0 
MODELO_IA = None; CACHE_IA = {}; USAR_IA = False

def configurar_ia(api_key):
    global MODELO_IA, USAR_IA
    if not api_key or "PON_AQUI" in api_key: USAR_IA = False; return
    try:
        genai.configure(api_key=api_key)
        MODELO_IA = genai.GenerativeModel('gemini-pro')
        USAR_IA = True
        print("🤖 CORE: IA Gemini conectada.")
    except: USAR_IA = False

def cargar_modelo(ruta):
    print(f"🔄 CORE: Cargando {ruta}...")
    return ifcopenshell.open(ruta)

def obtener_peso_neto(elemento):
    psets = ifcopenshell.util.element.get_psets(elemento)
    for ps in psets.values():
        for key, val in ps.items():
            k = key.lower()
            if isinstance(val, (int, float)) and val > 0:
                if "netweight" in k: return float(val) 
                if "mass" in k: return float(val)      
    for ps in psets.values():
        val = ps.get("NetVolume", ps.get("Volume", 0))
        if isinstance(val, (int, float)) and val > 0: return float(val) * DENSIDAD_ACERO
    return 0.0

def obtener_propiedad(elemento, nombres_posibles):
    """Busca una propiedad en los Psets del elemento."""
    psets = ifcopenshell.util.element.get_psets(elemento)
    for ps in psets.values():
        for k, v in ps.items():
            if k in nombres_posibles and v: return str(v)
    return ""

def obtener_tag(elemento):
    """Obtiene el TAG (Marca de Parte). Ej: p102, m30, C1 (si es pieza suelta)."""
    # Tekla suele exportar el Tag en 'Mark', 'Reference' o 'Part Position'
    tag = obtener_propiedad(elemento, ["Mark", "Reference", "Pos", "Part Position", "Part Mark"])
    if not tag: 
        if elemento.Name and len(elemento.Name) < 15: return elemento.Name
        return f"ID-{elemento.id()}"
    return tag

def obtener_assembly_mark(elemento, padre=None):
    """Obtiene el ASSEMBLY MARK (Marca de Conjunto). Ej: C1, V20."""
    # 1. Si tiene padre (Assembly), la marca del padre es la que manda.
    if padre:
        asm_mark = obtener_propiedad(padre, ["Assembly/Cast unit Mark", "Assembly Mark", "Mark"])
        if asm_mark: return asm_mark
        
    # 2. Si es un elemento suelto, intentamos buscar su propia Assembly Mark
    asm_mark = obtener_propiedad(elemento, ["Assembly/Cast unit Mark", "Assembly Mark"])
    if asm_mark: return asm_mark
    
    # 3. Si no tiene, asumimos que es una pieza suelta y su Tag es su Assembly Mark
    return obtener_tag(elemento)

def obtener_altura_real(elemento, padre=None):
    objetos = [elemento]
    if padre: objetos.append(padre)
    claves = ["Assembly/Cast unit bottom elevation", "Bottom elevation", "Elevation"]
    for obj in objetos:
        psets = ifcopenshell.util.element.get_psets(obj)
        for ps in psets.values():
            for k in claves:
                if k in ps:
                    try:
                        v = float(str(ps[k]).replace('+', ''))
                        if abs(v) < 200: return v * 1000.0
                        return v
                    except: pass
    try:
        return ifcopenshell.util.placement.get_local_placement(elemento.ObjectPlacement)[2][3]
    except: return 0.0

def obtener_perfil_real(elemento):
    if hasattr(elemento, "Description") and elemento.Description: return str(elemento.Description)
    prof = obtener_propiedad(elemento, ["Profile", "Profile Name"])
    if prof: return prof
    if hasattr(elemento, "ObjectType") and elemento.ObjectType: return str(elemento.ObjectType)
    return str(elemento.Name) if elemento.Name else "S/N"

def es_placa_confirmada(elemento):
    p = obtener_perfil_real(elemento).upper().strip()
    return p.startswith("PL") or p.startswith("FL") or "PLATE" in p or "CHAPA" in p or "PLANCHA" in p

def es_tornillo_estricto(elemento):
    if es_placa_confirmada(elemento): return False
    if elemento.is_a("IfcMechanicalFastener"): return True
    p = obtener_perfil_real(elemento).upper()
    n = (elemento.Name or "").upper()
    txt = n + " " + p
    bad = ["BOLT", "NUT", "WASHER", "TORNILLO", "TUERCA", "ARANDELA", "ANCHOR", "ROD"]
    return any(x in txt for x in bad)

def clasificar_elemento(elemento):
    if es_placa_confirmada(elemento): return "PLACA"
    p = obtener_perfil_real(elemento).upper().replace(" ", "")
    if any(x in p for x in ["IPE","HEA","HEB","UPN","SHS","RHS","TUBO","HSS","W","UB","UC","ANGULO"]): return "LAMINADO"
    if len(p) > 1 and p[0] == "L" and p[1].isdigit(): return "LAMINADO"
    if "REJILLA" in p or "TRAMEX" in p: return "REJILLA"
    return "GENERICO"

def extraer_datos_bcs(ifc_file):
    print("🧠 CORE: Extrayendo datos (Separando TAG vs ASSEMBLY MARK)...")
    datos = []
    
    # 1. CONTENEDORES (Assemblies + Anclajes)
    contenedores = ifc_file.by_type("IfcElementAssembly") + ifc_file.by_type("IfcMechanicalFastener")
    ids_procesados = set()

    for asm in contenedores:
        partes = []
        # Buscamos partes hijas
        if asm.IsDecomposedBy:
            for rel in asm.IsDecomposedBy: 
                for hijo in rel.RelatedObjects:
                    if not es_tornillo_estricto(hijo): partes.append(hijo)
        
        # Si no tiene hijos válidos, miramos si el propio assembly es válido
        if not partes:
            if not es_tornillo_estricto(asm): partes = [asm]
            else: continue

        # PROCESAMOS CADA PARTE INDIVIDUALMENTE
        for parte in partes:
            ids_procesados.add(parte.id())
            ids_procesados.add(asm.id())
            
            w = obtener_peso_neto(parte)
            if w <= 0.001 and es_placa_confirmada(parte): w = 1.0
            
            if w > 0.001:
                cat = clasificar_elemento(parte)
                perfil = obtener_perfil_real(parte)
                z = obtener_altura_real(parte, padre=asm)
                
                # --- LA CLAVE ---
                tag = obtener_tag(parte)                    # Ej: p102
                asm_mark = obtener_assembly_mark(parte, asm) # Ej: C1
                
                datos.append({
                    "objeto_ifc": parte, "partes_hijas": [parte], 
                    "referencia": tag,            # PARA 5D y 6D (Detalle)
                    "assembly_mark": asm_mark,    # PARA 4D (Agrupación)
                    "categoria": cat, "peso_kg": w, "altura_z": z, "es_tornillo": False,
                    "perfil_maestro": perfil
                })

    # 2. SUELTOS
    tipos = ["IfcBeam", "IfcColumn", "IfcPlate", "IfcMember", "IfcDiscreteAccessory", "IfcBuildingElementProxy"]
    sueltos = []
    for t in tipos: sueltos.extend(ifc_file.by_type(t))
    
    for elem in sueltos:
        if elem.id() in ids_procesados: continue
        if es_tornillo_estricto(elem): continue
        w = obtener_peso_neto(elem)
        if w <= 0.001 and es_placa_confirmada(elem): w = 1.0

        if w > 0.001:
            cat = clasificar_elemento(elem)
            perfil = obtener_perfil_real(elem)
            z = obtener_altura_real(elem)
            
            tag = obtener_tag(elem)
            asm_mark = obtener_assembly_mark(elem, None) # Suelto = él mismo

            datos.append({
                "objeto_ifc": elem, "partes_hijas": [elem],
                "referencia": tag,
                "assembly_mark": asm_mark,
                "categoria": cat, "peso_kg": w, "altura_z": z, "es_tornillo": False,
                "perfil_maestro": perfil
            })

    print(f"✅ CORE: {len(datos)} partes extraídas con Tag y Assembly Mark.")
    return datos

# --- FUNCIÓN DE COMPATIBILIDAD (PARA ARREGLAR EL ERROR DE APP.PY) ---
def extraer_datos_modelo(ruta_ifc):
    """
    Esta función es un 'puente' para que el app.py encuentre el nombre que busca.
    Usa tu lógica avanzada pero devuelve lo que app.py espera (datos, modelo).
    """
    # 1. Cargamos el modelo usando tu función existente
    modelo = cargar_modelo(ruta_ifc)
    
    # 2. Extraemos los datos usando tu función avanzada existente
    datos = extraer_datos_bcs(modelo)
    
    # 3. Devolvemos la tupla (datos, modelo) para satisfacer a app.py
    return datos, modelo