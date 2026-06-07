"""
ANR Paraguay Electoral Roll Lookup
Consulta individual del padrón electoral 2026 de la ANR (Asociación Nacional Republicana) de Paraguay
"""

import json
import requests
from typing import Dict, List, Optional, Union, Tuple

class ANRLookup:
    def __init__(self, base_url: str = "https://www.anr.org.py"):
        self.base_url = base_url
        self.duplicado_cache: Optional[List[Dict]] = None
        self.location_data: Dict[str, List[Dict]] = {}  # Para almacenar departamentos, distritos, etc.
    
    def _fetch_json(self, url: str) -> Optional[Union[Dict, List]]:
        """Obtiene y parsea un JSON desde una URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON desde {url}: {e}")
            return None
    
    def load_duplicados(self) -> Optional[List[Dict]]:
        """Carga la lista de cédulas duplicadas"""
        if self.duplicado_cache is not None:
            return self.duplicado_cache
        
        url = f"{self.base_url}/assets/p2026/duplicado.json"
        data = self._fetch_json(url)
        if data is None:
            return None
        
        # Aseguramos que sea una lista
        if isinstance(data, list):
            self.duplicado_cache = data
            return self.duplicado_cache
        else:
            print("Error: duplicado.json no es una lista")
            return None
    
    def load_location_data(self) -> bool:
        """Carga los datos de referencia geográfica (departamentos, distritos, etc.)"""
        endpoints = ['departamento', 'distrito', 'seccional', 'local']
        
        for endpoint in endpoints:
            url = f"{self.base_url}/assets/p2026/{endpoint}.json"
            data = self._fetch_json(url)
            if data is None:
                print(f"Error al cargar {endpoint}.json")
                return False
            
            # Aseguramos que sea una lista
            if not isinstance(data, list):
                print(f"Error: {endpoint}.json no es una lista")
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
        # Limpiar la cédula
        cedula = cedula.strip()
        if not cedula.isdigit():
            return False, None, "La cédula debe contener solo números"
        
        cedula_int = int(cedula)
        
        # Primero verificar si es un duplicado
        duplicados = self.load_duplicados()
        if duplicados is None:
            return False, None, "No se pudo cargar la lista de duplicados"
        
        duplicado_matches = [item for item in duplicados if item.get('cedula') == cedula_int]
        
        if duplicado_matches:
            # Es un caso de duplicado, retornamos el primero por ahora
            # (en una implementación completa, mostraríamos todos)
            return True, duplicado_matches[0], ""
        
        # Si no es duplicado, buscar en la estructura jerárquica
        # Construir ruta: assets/p2026/[d1]/[d2]/[d3]/[d4]/[cedula].json
        if len(cedula) < 4:
            return False, None, "La cédula debe tener al menos 4 dígitos"
        
        path_parts = list(cedula[:4])
        path = "/".join(path_parts)
        url = f"{self.base_url}/assets/p2026/{path}/{cedula}.json"
        
        data = self._fetch_json(url)
        if data is None:
            return False, None, "Afiliado no encontrado"
        
        # Aseguramos que sea un dict
        if not isinstance(data, dict):
            print("Error: los datos del afiliado no son un diccionario")
            return False, None, "Formato de datos inválido"
        
        return True, data, ""
    
    def formatear_resultado(self, data: Dict) -> Dict:
        """Formatea los datos del resultado para mostrar"""
        if not data:
            return {}
        
        # Formatear fecha
        fecha_nac = data.get('nacimiento', '')
        if fecha_nac:
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha_nac, '%Y-%m-%d')
                fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
            except:
                fecha_formateada = fecha_nac
        else:
            fecha_formateada = ''
        
        # Obtener descripciones (si tenemos los datos de referencia)
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
            'cedula': data.get('cedula', ''),
            'nombres': data.get('nombres', ''),
            'apellidos': data.get('apellidos', ''),
            'fecha_nacimiento': fecha_formateada,
            'departamento': f"{data.get('departamento', '')} - {departamento_desc}",
            'distrito': f"{data.get('distrito', '')} - {distrito_desc}",
            'seccional': data.get('seccional', ''),
            'local': f"{data.get('local', '')} - {local_desc}",
            'mesa': data.get('mesa', ''),
            'orden': data.get('orden', '')
        }

def main():
    """Función principal para uso desde línea de comandos"""
    import sys
    
    if len(sys.argv) != 2:
        print("Uso: python anr_lookup.py <numero_de_cedula>")
        sys.exit(1)
    
    cedula = sys.argv[1]
    lookup = ANRLookup()
    
    print(f"Buscando cédula: {cedula}")
    success, data, error = lookup.buscar_por_cedula(cedula)
    
    if success and data:
        resultado = lookup.formatear_resultado(data)
        print("\nResultado de la consulta:")
        print("-" * 40)
        for clave, valor in resultado.items():
            print(f"{clave.replace('_', ' ').title()}: {valor}")
    else:
        print(f"Error: {error}")

if __name__ == "__main__":
    main()