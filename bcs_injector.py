# bcs_injector.py
import ifcopenshell
import ifcopenshell.api
import datetime

# --- MAPEO UNICLASS 2015 (Estándar ISO 19650) ---
MAPEO_UNICLASS = {
    "LAMINADO":    "Pr_20_29_87_82", 
    "PLACA":       "Pr_20_29_87_63", 
    "TORNILLERIA": "Pr_20_29_33_05", 
    "REJILLA":     "Pr_30_59_32_33", 
    "GENERICO":    "Pr_20_29_87"     
}

# CAMBIO CLAVE: Añadidos argumentos con valores por defecto para que no falle
def generar_ifc_enriquecido(ifc_file, ruta_salida, datos, iso_status="S2", iso_suitability="Para Información"):
    print(f"💉 INJECTOR: Generando IFC final '{ruta_salida}'...")
    print(f"   -> Configuración ISO: Status={iso_status} | Uso={iso_suitability}")
    
    count = 0
    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
    
    # Nombres de Psets
    PSET_TECNICO = "BCS_DATOS_TECNICOS"
    PSET_COSTES  = "BCS_5D_COSTES"
    PSET_HUELLA  = "BCS_6D_SOSTENIBILIDAD"
    PSET_GESTION = "ISO_19650_STATUS"
    PSET_4D      = "BCS_4D_PLANIFICACION"
    
    for item in datos:
        element = item["objeto_ifc"]
        cat = item.get("categoria", "GENERICO")
        
        # --- 1. PREPARACIÓN DE DATOS ---
        
        # A) Datos de Gestión (Usando las variables que llegan de la App)
        uniclass = MAPEO_UNICLASS.get(cat, MAPEO_UNICLASS["GENERICO"])
        props_gestion = {
            "Status": iso_status,                # <--- DATO DINÁMICO
            "Suitability": iso_suitability,      # <--- DATO DINÁMICO
            "Revision": "P01", 
            "Uniclass2015_Code": uniclass
        }

        # B) Datos Técnicos
        props_tecnicas = {
            "BCS_Fecha_Calculo": fecha_hoy,
            "BCS_Ref_Pieza": str(item.get("referencia", "S/R")),
            "BCS_Ref_Conjunto": str(item.get("assembly_mark", "S/R")),
            "BCS_Perfil_Maestro": str(item.get("perfil_maestro", "Var")),
            "BCS_Categoria_Interna": cat
        }

        # C) Datos 4D (Planificación)
        props_4d = {}
        if "bcs_fecha_plan" in item and item["bcs_fecha_plan"]:
            fecha_obj = item["bcs_fecha_plan"]
            # Asegurar formato string YYYY-MM-DD
            fecha_str = fecha_obj.strftime("%Y-%m-%d") if hasattr(fecha_obj, 'strftime') else str(fecha_obj)
            
            props_4d["Fecha_Planificada"] = fecha_str
            props_4d["Fase_Constructiva"] = str(item.get("bcs_fase", "General"))

        # D) Datos 5D (Costes)
        props_costes = {}
        if "bcs_coste_item" in item:
            props_costes["Coste_Material_Eur"] = float(item["bcs_coste_item"])
            props_costes["Precio_Unitario"] = float(item.get("bcs_precio_unitario", 0.0))

        # E) Datos 6D (Sostenibilidad)
        props_huella = {}
        if "bcs_huella_item" in item:
            props_huella["Huella_Total_kgCO2eq"] = float(item["bcs_huella_item"])
            props_huella["Factor_Impacto_A1_A3"] = float(item.get("bcs_factor_impacto", 0.0))

        # --- 2. INYECCIÓN ---
        def inyectar_pset(nombre_pset, propiedades):
            if not propiedades: return
            try:
                # Intentar crear nuevo
                pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=element, name=nombre_pset)
                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties=propiedades)
            except:
                # Si falla (ya existe), buscar y editar
                try: 
                    for rel in element.IsDefinedBy:
                        if rel.is_a("IfcRelDefinesByProperties"):
                            defi = rel.RelatingPropertyDefinition
                            if defi.Name == nombre_pset:
                                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=defi, properties=propiedades)
                                break
                except: pass

        # Inyectamos todo en orden
        inyectar_pset(PSET_GESTION, props_gestion)
        inyectar_pset(PSET_TECNICO, props_tecnicas)
        inyectar_pset(PSET_4D, props_4d)      # <--- AQUÍ ENTRA EL 4D
        inyectar_pset(PSET_COSTES, props_costes)
        inyectar_pset(PSET_HUELLA, props_huella)
        
        count += 1

    ifc_file.write(ruta_salida)
    print(f"✅ INJECTOR: Archivo guardado correctamente ({count} elementos procesados).")