import streamlit as st
import requests
import json
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── brand colors ──────────────────────────────────────────────────────────────
PRIMARY   = "#C0392B"   # deep red
ACCENT    = "#E67E22"   # warm orange
LIGHT_BG  = "#FFF8F5"
TEXT_DARK = "#2C1810"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;900&family=Open+Sans:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Open Sans', sans-serif;
    color: {TEXT_DARK};
}}

/* ── hero banner ── */
.hero-banner {{
    background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%);
    border-radius: 16px;
    padding: 28px 24px 20px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0 6px 24px rgba(192,57,43,0.35);
}}
.hero-banner h1 {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 2rem;
    margin: 8px 0 4px;
    letter-spacing: -0.5px;
}}
.hero-banner p {{
    font-size: 0.95rem;
    opacity: 0.92;
    margin: 0;
}}

/* ── candidate card ── */
.candidate-card {{
    background: white;
    border: 3px solid {PRIMARY};
    border-radius: 14px;
    padding: 20px 18px;
    text-align: center;
    box-shadow: 0 4px 18px rgba(192,57,43,0.18);
    margin-bottom: 12px;
}}
.candidate-card .badge {{
    display: inline-block;
    background: {ACCENT};
    color: white;
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 1.1rem;
    border-radius: 8px;
    padding: 4px 14px;
    margin-bottom: 6px;
    letter-spacing: 1px;
}}
.candidate-card .name {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 1.35rem;
    color: {PRIMARY};
    margin: 2px 0;
}}
.candidate-card .role {{
    font-size: 0.88rem;
    color: #888;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ── search box ── */
.stTextInput > div > div > input {{
    border: 2px solid {PRIMARY} !important;
    border-radius: 10px !important;
    font-size: 1.05rem !important;
    padding: 10px 14px !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, {PRIMARY}, {ACCENT}) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 10px 28px !important;
    width: 100%;
    box-shadow: 0 4px 12px rgba(192,57,43,0.3) !important;
    transition: opacity .2s;
}}
.stButton > button:hover {{ opacity: 0.88; }}

/* ── result card ── */
.result-card {{
    background: {LIGHT_BG};
    border: 2px solid {ACCENT};
    border-radius: 12px;
    padding: 18px 20px;
    margin-top: 12px;
}}
.result-card .field-label {{
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: {ACCENT};
    letter-spacing: 0.6px;
    margin-bottom: 1px;
}}
.result-card .field-value {{
    font-size: 1rem;
    font-weight: 600;
    color: {TEXT_DARK};
    margin-bottom: 10px;
}}

/* ── footer ── */
.footer {{
    text-align: center;
    color: #aaa;
    font-size: 0.78rem;
    margin-top: 30px;
    padding-top: 12px;
    border-top: 1px solid #eee;
}}
</style>
"""

# ── ANR Lookup (unchanged logic) ──────────────────────────────────────────────
class ANRLookup:
    def __init__(self, base_url: str = "https://www.anr.org.py"):
        self.base_url = base_url
        self.duplicado_cache: Optional[List[Dict]] = None
        self.location_data: Dict[str, List[Dict]] = {}

    def _fetch_json(self, url: str) -> Optional[Union[Dict, List]]:
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
        if self.duplicado_cache is not None:
            return self.duplicado_cache
        url = f"{self.base_url}/assets/p2026/duplicado.json"
        data = self._fetch_json(url)
        if data is None:
            return None
        if isinstance(data, list):
            self.duplicado_cache = data
            return self.duplicado_cache
        st.error("Error: duplicado.json no es una lista")
        return None

    def load_location_data(self) -> bool:
        endpoints = ['departamento', 'distrito', 'seccional', 'local']
        urls = {ep: f"{self.base_url}/assets/p2026/{ep}.json" for ep in endpoints}
        results: Dict[str, Optional[Union[Dict, List]]] = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            fut = {executor.submit(self._fetch_json, url): ep for ep, url in urls.items()}
            for f in as_completed(fut):
                ep = fut[f]
                results[ep] = f.result()

        for ep in endpoints:
            data = results.get(ep)
            if data is None or not isinstance(data, list):
                st.error(f"Error al cargar {ep}.json")
                return False
            self.location_data[ep] = data
        return True

    def get_departamento_desc(self, codigo: int) -> str:
        for dept in self.location_data.get('departamento', []):
            if dept.get('departamento') == codigo:
                return dept.get('descripcion', '')
        return ''

    def get_distrito_desc(self, departamento: int, distrito: int) -> str:
        for dist in self.location_data.get('distrito', []):
            if dist.get('departamento') == departamento and dist.get('distrito') == distrito:
                return dist.get('descripcion', '')
        return ''

    def get_local_desc(self, departamento: int, distrito: int, seccional: int, local: int) -> str:
        for loc in self.location_data.get('local', []):
            if (loc.get('departamento') == departamento and
                loc.get('distrito') == distrito and
                loc.get('seccional') == seccional and
                loc.get('local') == local):
                return loc.get('descripcion', '')
        return ''

    def buscar_por_cedula(self, cedula: str) -> Tuple[bool, Optional[Dict], str]:
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
        path = "/".join(list(cedula[:4]))
        url = f"{self.base_url}/assets/p2026/{path}/{cedula}.json"
        data = self._fetch_json(url)
        if data is None:
            return False, None, "Afiliado no encontrado"
        if not isinstance(data, dict):
            return False, None, "Formato de datos inválido"
        return True, data, ""

    def formatear_resultado(self, data: Dict) -> Dict:
        if not data:
            return {}
        fecha_nac = data.get('nacimiento', '')
        if fecha_nac:
            try:
                fecha_formateada = datetime.strptime(fecha_nac, '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                fecha_formateada = fecha_nac
        else:
            fecha_formateada = ''
        dep = data.get('departamento', 0)
        dis = data.get('distrito', 0)
        sec = data.get('seccional', 0)
        loc = data.get('local', 0)
        return {
            'Cédula':        data.get('cedula', ''),
            'Nombres':       data.get('nombres', ''),
            'Apellidos':     data.get('apellidos', ''),
            'Nacimiento':    fecha_formateada,
            'Departamento':  f"{dep} – {self.get_departamento_desc(dep)}",
            'Distrito':      f"{dis} – {self.get_distrito_desc(dep, dis)}",
            'Seccional':     sec,
            'Local':         f"{loc} – {self.get_local_desc(dep, dis, sec, loc)}",
            'Mesa':          data.get('mesa', ''),
            'Orden':         data.get('orden', ''),
        }

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Padrón ANR 2026 · Marce Centurión",
        page_icon="🇵🇾",
        layout="centered"
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-banner">
        <div style="font-size:2.2rem;">🇵🇾</div>
        <h1>Consulta Padrón ANR 2026</h1>
        <p>Internas Municipales · 7 de Junio de 2026 · Asunción</p>
    </div>
    """, unsafe_allow_html=True)

    # ── CANDIDATE CARD ────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="medium")
    with col_a:
        st.markdown("""
        <div class="candidate-card">
            <div class="badge">LISTA 2 · MHC</div>
            <div class="name">Camilo Pérez</div>
            <div class="role">Candidato a Intendente</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="candidate-card">
            <div class="badge">LISTA 2P · OPCIÓN 4</div>
            <div class="name">Marce Centurión</div>
            <div class="role">Candidato a Concejal</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PADRON SEARCH ─────────────────────────────────────────────────────────
    st.markdown("### 🔎 Consultá tu lugar de votación")
    st.caption("Ingresá tu cédula para saber tu mesa, local y orden en el padrón.")

    if 'lookup' not in st.session_state:
        st.session_state.lookup = ANRLookup()
        with st.spinner("Cargando datos de referencia…"):
            st.session_state.lookup.load_location_data()

    if 'resultado' not in st.session_state:
        st.session_state.resultado = None

    lookup = st.session_state.lookup

    cedula_input = st.text_input(
        "Número de cédula de identidad",
        placeholder="Ej: 4568XXX",
        label_visibility="collapsed",
        key="cedula_input"
    )

    col_btn, _ = st.columns([1, 2])
    with col_btn:
        buscar = st.button("🔍  Consultar padrón", use_container_width=True)

    if buscar:
        if cedula_input:
            with st.spinner("Buscando…"):
                success, data, error = lookup.buscar_por_cedula(cedula_input)
            if success and data:
                st.session_state.resultado = lookup.formatear_resultado(data)
            else:
                st.session_state.resultado = None
                st.error(f"❌ {error}")
        else:
            st.warning("⚠️ Por favor ingresá un número de cédula")

    r = st.session_state.resultado

    st.markdown(
        f'<div class="result-card">'
        f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 20px;">'
        f'    <div><div class="field-label">Cédula</div><div class="field-value">{r["Cédula"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Nombres</div><div class="field-value">{r["Nombres"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Apellidos</div><div class="field-value">{r["Apellidos"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Nacimiento</div><div class="field-value">{r["Nacimiento"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Departamento</div><div class="field-value">{r["Departamento"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Distrito</div><div class="field-value">{r["Distrito"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Seccional</div><div class="field-value">{r["Seccional"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Local</div><div class="field-value">{r["Local"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Mesa</div><div class="field-value">{r["Mesa"] if r else "—"}</div></div>'
        f'    <div><div class="field-label">Orden</div><div class="field-value">{r["Orden"] if r else "—"}</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if r:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{PRIMARY},{ACCENT});
                    color:white;border-radius:12px;padding:16px 20px;
                    margin-top:16px;text-align:center;">
            <div style="font-family:'Montserrat',sans-serif;font-weight:900;
                        font-size:1.1rem;margin-bottom:4px;">
                ¡No olvidés votar Lista 2P · Opción 4!
            </div>
            <div style="font-size:0.9rem;opacity:.92;">
                <strong>Marce Centurión</strong> — Concejal por Asunción
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── VOTING GUIDE ──────────────────────────────────────────────────────────
    with st.expander("📋 ¿Cómo votar este domingo? — Guía paso a paso", expanded=True):
        for i in range(1, 9):
            img_path = f"img/{i}.jpg"
            st.image(img_path, width=700)
            st.caption(f"**Paso {i}**")

    # ── DISCLAIMER ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#FEF3E2;border:1px solid #E89F4A;border-radius:10px;
                padding:12px 16px;margin-top:20px;font-size:0.82rem;color:#7B4800;">
        <strong>⚠️ Aviso legal</strong><br><br>
        <strong>Naturaleza privada:</strong> Esta es una aplicación de carácter privado y particular,
        desarrollada con fines informativos. No tiene vínculo oficial con la ANR, el TSJE ni ningún
        organismo electoral.<br><br>
        <strong>Responsabilidad del usuario:</strong> El uso de esta herramienta es bajo
        exclusiva responsabilidad del usuario. El desarrollador no se hace responsable por el uso
        que terceros puedan darle a la información aquí consultada, ni por decisiones tomadas en
        base a ella.<br><br>
        <strong>Datos:</strong> La información proviene del sitio público
        <a href="https://www.anr.org.py" target="_blank">www.anr.org.py</a>.
        Esta aplicación no almacena ni re-publica datos personales — cada consulta se realiza
        en vivo contra los servidores de la ANR.<br><br>
        <strong>Contenido político:</strong> Esta aplicación contiene propaganda política
        (Lista 2P · Opción 4 — Marce Centurión). El día de la elección, desde las 0 hs,
        está prohibida la difusión de propaganda electoral (Ley N° 834/96 y modificaciones).
        Esta herramienta debe utilizarse exclusivamente antes del inicio de la veda electoral.<br><br>
        <strong>Recordá:</strong> Podés votar por lista distinta para Intendente y para Concejales.
        No tenés que votar a la misma lista en ambas categorías.
    </div>
    """, unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer">
        Consulta informativa · Datos fuente: <a href="https://www.anr.org.py" target="_blank">www.anr.org.py</a><br>
        Marce Centurión · Concejal · Lista 2P Opción 4
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
