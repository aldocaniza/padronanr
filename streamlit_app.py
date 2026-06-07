import streamlit as st
import requests
import json
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime

class ANRLookup:
    def __init__(self, base_url: str = "https://www.anr.org.py"):
        self.base_url = base_url
        self.duplicado_cache: Optional[List[Dict]] = None
        self.location_data: Dict[str, List[Dict]] = {}
    
    def _fetch_json(self, url: str) -> Optional[Union[Dict, List]]:
        """Obtiene y parsea un JSON desde una URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error al obtener {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            st.error(f"Error al decodificar JSON desde {url}: {e}")
            return None
    
    def load_duplicados(self) -> Optional[List[Dict]]:
        """Carga la lista de cédulas duplicadas"""
        if self.duplicado_cache is not None:
            return self.duplicado_cache
        
        url = f"{self.base_url}/assets/p2026/duplicado.json"
        data = self._fetch_json(url)
        if data is None:
            return None
        
        if isinstance(data, list):
            self.duplicado_cache = data
            return self.duplicado_cache
        else:
            st.error("Error: duplicado.json no es una lista")
            return None
    
    def load_location_data(self) -> bool:
        """Carga los datos de referencia geográfica"""
        endpoints = ['departamento', 'distrito', 'seccional', 'local']
        
        for endpoint in endpoints:
            url = f"{self.base_url}/assets/p2026/{endpoint}.json"
            data = self._fetch_json(url)
            if data is None:
                st.error(f"Error al cargar {endpoint}.json")
                return False
            
            if not isinstance(data, list):
                st.error(f"Error: {endpoint}.json no es una lista")
                return False
                
            self.location_data[endpoint] = data
        
        return True
    
    def get_departamento_desc(self, codigo: int) -> str:
        """Obtiene la descripción del departamento por su código"""
        for dept in self.location_data.get('departamento', []):
            if dept.get('departamento') == codigo:
                return dept.get('descripcion', '')
        return ''
    
    def get_distrito_desc(self, departamento: int, distrito: int) -> str:
        """Obtiene la descripción del distrito por sus códigos"""
        for dist in self.location_data.get('distrito', []):
            if dist.get('departamento') == departamento and dist.get('distrito') == distrito:
                return dist.get('descripcion', '')
        return ''
    
    def get_local_desc(self, departamento: int, distrito: int, seccional: int, local: int) -> str:
        """Obtiene la descripción del local por sus códigos"""
        for loc in self.location_data.get('local', []):
            if (loc.get('departamento') == departamento and 
                loc.get('distrito') == distrito and 
                loc.get('seccional') == seccional and 
                loc.get('local') == local):
                return loc.get('descripcion', '')
        return ''
    
    def buscar_por_cedula(self, cedula: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Busca un afiliado por cédula de identidad
        
        Returns:
            Tuple[success, data, error_message]
        """
        cedula = cedula.strip()
        if not cedula.isdigit():
            return False, None, "La cédula debe contener solo números"
        
        cedula_int = int(cedula)
        
        duplicados = self.load_duplicados()
        if duplicados is None:
            return False, None, "No se pudo cargar la lista de duplicados"
        
        duplicado_matches = [item for item in duplicados if item.get('cedula') == cedula_int]
        
        if duplicado_matches:
            return True, duplicado_matches[0], ""
        
        if len(cedula) < 4:
            return False, None, "La cédula debe tener al menos 4 dígitos"
        
        path_parts = list(cedula[:4])
        path = "/".join(path_parts)
        url = f"{self.base_url}/assets/p2026/{path}/{cedula}.json"
        
        data = self._fetch_json(url)
        if data is None:
            return False, None, "Afiliado no encontrado"
        
        if not isinstance(data, dict):
            st.error("Error: los datos del afiliado no son un diccionario")
            return False, None, "Formato de datos inválido"
        
        return True, data, ""
    
    def formatear_resultado(self, data: Dict) -> Dict:
        """Formatea los datos del resultado para mostrar"""
        if not data:
            return {}
        
        fecha_nac = data.get('nacimiento', '')
        if fecha_nac:
            try:
                fecha_obj = datetime.strptime(fecha_nac, '%Y-%m-%d')
                fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
            except:
                fecha_formateada = fecha_nac
        else:
            fecha_formateada = ''
        
        departamento_desc = self.get_departamento_desc(data.get('departamento', 0))
        distrito_desc = self.get_distrito_desc(
            data.get('departamento', 0), 
            data.get('distrito', 0)
        )
        local_desc = self.get_local_desc(
            data.get('departamento', 0),
            data.get('distrito', 0),
            data.get('seccional', 0),
            data.get('local', 0)
        )
        
        return {
            'Cédula de Identidad': data.get('cedula', ''),
            'Nombres': data.get('nombres', ''),
            'Apellidos': data.get('apellidos', ''),
            'Fecha de Nacimiento': fecha_formateada,
            'Departamento': f"{data.get('departamento', '')} - {departamento_desc}",
            'Distrito': f"{data.get('distrito', '')} - {distrito_desc}",
            'Seccional': data.get('seccional', ''),
            'Local': f"{data.get('local', '')} - {local_desc}",
            'Mesa': data.get('mesa', ''),
            'Orden': data.get('orden', '')
        }

def main():
    st.set_page_config(
        page_title="Consulta Padrón ANR 2026",
        page_icon="🇵🇾",
        layout="centered"
    )
    
    st.title("🇵🇾 Consulta Padrón Electoral ANR 2026")
    st.subheader("Padrón Internas Municipales del 7 de Junio del 2026")
    
    # Inicializar el lookup
    if 'lookup' not in st.session_state:
        st.session_state.lookup = ANRLookup()
        with st.spinner("Cargando datos de referencia..."):
            st.session_state.lookup.load_location_data()
    
    lookup = st.session_state.lookup
    
    # Input para la cédula
    cedula_input = st.text_input(
        "Ingrese el número de cédula de identidad:",
        placeholder="Ej: 4568521",
        help="Ingrese solo números, sin espacios ni guiones"
    )
    
    # Botón de búsqueda
    if st.button("🔍 Consultar", type="primary"):
        if cedula_input:
            with st.spinner("Buscando información..."):
                success, data, error = lookup.buscar_por_cedula(cedula_input)
                
                if success and data:
                    resultado = lookup.formatear_resultado(data)
                    
                    st.success("✅ Afiliado encontrado")
                    
                    # Mostrar resultados en formato de tarjeta
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**Cédula:** {resultado.get('Cédula de Identidad', 'N/A')}")
                        st.info(f"**Nombre:** {resultado.get('Nombres', 'N/A')}")
                        st.info(f"**Apellido:** {resultado.get('Apellidos', 'N/A')}")
                        st.info(f"**Fecha Nac.:** {resultado.get('Fecha de Nacimiento', 'N/A')}")
                    
                    with col2:
                        st.info(f"**Departamento:** {resultado.get('Departamento', 'N/A')}")
                        st.info(f"**Distrito:** {resultado.get('Distrito', 'N/A')}")
                        st.info(f"**Seccional:** {resultado.get('Seccional', 'N/A')}")
                        st.info(f"**Local:** {resultado.get('Local', 'N/A')}")
                    
                    st.info(f"**Mesa:** {resultado.get('Mesa', 'N/A')}")
                    st.info(f"**Orden:** {resultado.get('Orden', 'N/A')}")
                    
                else:
                    st.error(f"❌ {error}")
        else:
            st.warning("⚠️ Por favor ingrese un número de cédula")
    
    # Información adicional
    with st.expander("ℹ️ Información sobre el padrón"):
        st.write("""
        Este sistema permite consultar individualmente el padrón electoral de las 
        elecciones internas de la ANR (Asociación Nacional Republicana) correspondientes 
        al 7 de junio de 2026.
        
        **Cómo funciona:**
        - Los datos están estructurados en archivos JSON organizados jerárquicamente
        - La ruta se construye usando los primeros 4 dígitos de la cédula
        - Ejemplo: para cédula 4568521 → assets/p2026/4/5/6/8/4568521.json
        
        **Limitaciones:**
        - Solo permite consultas individuales
        - No hay descarga masiva disponible públicamente
        - Requiere conexión a internet para acceder a los datos
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Desarrollado para consulta educativa | Datos fuente: www.anr.org.py"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()