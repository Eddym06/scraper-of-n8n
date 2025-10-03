#!/usr/bin/env python3
"""
N8N COMPREHENSIVE WORKFLOW SCRAPER - V3.1 (CONTEO DE NODOS MEJORADO)

NUEVA FUNCIONALIDAD V3.1:
🎯 SISTEMA DE CONTEO DE NODOS MEJORADO - Investigación MCP Playwright
   - Investigación DOM completa de la estructura de n8n.io workflow cards
   - Fórmula correcta: NODOS VISIBLES + INDICADOR +X = TOTAL NODOS
   - Método 1: Detecta nodos con tooltips (li:has([role="tooltip"]))
   - Método 2: Detecta indicador +X (li span:not([role]))
   - Método 3: Suma ambos valores para el conteo total preciso
   - Antes: Solo detectaba indicador +X (subestimación)
   - Ahora: Conteo completo y preciso de todos los nodos

FUNCIONALIDADES V3.0 EXISTENTES:
1. EXPLORACIÓN SISTEMÁTICA de TODAS las categorías principales
2. EXPLORACIÓN AUTOMÁTICA de TODAS las subcategorías 
3. MAPEO DINÁMICO de la estructura completa de n8n.io/workflows
4. DESCARGA de workflows de TODAS las categorías, no solo AI Agent
5. LOGGING DETALLADO del progreso por categoría/subcategoría

CATEGORÍAS PRINCIPALES A EXPLORAR (CON SUBCATEGORÍAS HARDCODEADAS):
- Sales (3 subcategorías: CRM, Lead Generation, Lead Nurturing)
- Marketing (3 subcategorías: Content Creation, Market Research, Social Media)
- IT Ops (3 subcategorías: SecOps, Engineering, DevOps)
- Document Ops (3 subcategorías: Document Extraction, File Management, Invoice Processing)
- Support (3 subcategorías: Support Chatbot, Ticket Management, Internal Wiki)
- Other (5 subcategorías: Crypto Trading, HR, Miscellaneous, Personal Productivity, Project Management)

NOTA: La categoría AI está EXCLUIDA intencionalmente ya que fue procesada completamente 
en versiones anteriores del script.

TOTAL: 6 categorías principales con 20 subcategorías específicas identificadas mediante
investigación exhaustiva con MCP Playwright y análisis JavaScript DOM.

ESTRATEGIA EXPANDIDA:
- Fase 1: Mapear todas las categorías y subcategorías
- Fase 2: Para cada categoría/subcategoría:
  * Recopilar todos los workflows
  * Cargar todas las páginas ("Load more templates")
  * Descargar cada 15 workflows encontrados
- Fase 3: Estadísticas completas por categoría

Autor: Sistema de IA Avanzado  
Fecha: Enero 2025
Versión: 3.1 (CONTEO DE NODOS MEJORADO)
"""

import json
import re
import time
import pathlib
from typing import List, Optional, Dict, Any, Set, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from urllib.parse import urljoin, urlparse


class N8NComprehensiveWorkflowScraper:
    """Scraper expandido para exploración masiva de todas las categorías"""

    # URLs base
    BASE_URL = "https://n8n.io/workflows/"
    CATEGORIES_PAGE = "https://n8n.io/workflows/"
    
    # Configuración
    MIN_NODES = 6  
    SLOW_MO = 750  # Reducido para mayor velocidad
    TIMEOUT = 30000  # Aumentado a 30s para mejor conectividad
    MAX_TABS = 8
    DOWNLOAD_BATCH_SIZE = 15
    EXPLORATION_TABS = 2
    
    # Configuración específica para diferentes páginas
    WORKFLOWS_PER_PAGE = 30  # Para subcategorías usamos ?count=30
    MAX_WORKFLOWS_PER_SUBCATEGORY = 150  # Límite máximo por subcategoría

    def __init__(self, download_dir: str = "Workflow Scraper"):
        self.download_dir = pathlib.Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Estadísticas globales
        self.global_stats = {
            'categories_explored': 0,
            'subcategories_explored': 0,
            'total_workflows_found': 0,
            'total_workflows_downloaded': 0,
            'total_errors': 0,
            'start_time': time.time()
        }
        
        # Estadísticas por categoría
        self.category_stats = {}
        
        # Conjuntos para evitar duplicados
        self.processed_urls = set()
        self.downloaded_slugs = set()

    def log(self, message: str, level: str = "INFO") -> None:
        """Logging con timestamp y nivel"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def log_category(self, category: str, message: str, level: str = "INFO") -> None:
        """Logging específico por categoría"""
        timestamp = time.strftime("%H:%M:%S") 
        print(f"[{timestamp}] [{level}] [{category.upper()}] {message}")

    def accept_all_cookies(self, page: Page) -> None:
        """ACEPTAR todas las cookies para evitar bloqueos de contenido"""
        try:
            self.log("🍪 Buscando y ACEPTANDO cookies para evitar bloqueos...")
            
            page.wait_for_timeout(2000)
            
            accept_strategies = [
                "text=Accept All",
                "text=Accept all cookies", 
                "text=Accept All Cookies",
                "text=Accept",
                "text=I Agree",
                "text=Allow All",
                "text=Accept & Close",
                "button:has-text('Accept All')",
                "button:has-text('Accept')",
                "[data-testid='cookie-accept-all']",
                ".cookie-accept-all",
                "#cookie-accept-all",
                "[onclick*='accept']",
                ".cookiescript_accept_all",
                "button[class*='accept']",
                "div[class*='accept'][role='button']",
            ]

            for selector in accept_strategies:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        element.click()
                        page.wait_for_timeout(2000)
                        self.log(f"✅ Cookies ACEPTADAS con: {selector}")
                        return
                except Exception:
                    continue

            self.log("⚠️ No se encontraron cookies para aceptar (tal vez ya aceptadas)")

        except Exception as e:
            self.log(f"Error manejando cookies: {e}", "ERROR")

    def discover_main_categories(self, page: Page) -> List[Dict[str, str]]:
        """Descubre todas las categorías principales desde la página inicial"""
        self.log("🗺️ DESCUBRIENDO categorías principales...")
        
        try:
            # Múltiples intentos para navegar
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.log(f"🌐 Intento {attempt + 1}/{max_retries} - Navegando a: {self.CATEGORIES_PAGE}")
                    page.goto(self.CATEGORIES_PAGE, wait_until="networkidle", timeout=self.TIMEOUT)
                    page.wait_for_timeout(1500)  # Reducido de 2000 a 1500ms
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.log(f"❌ Error después de {max_retries} intentos: {e}", "ERROR")
                        # Si falla completamente, usar las categorías conocidas directamente
                        self.log("🔄 Usando categorías conocidas como fallback (EXCLUYENDO AI - ya procesada)")
                        known_categories = [
                            {'name': 'Sales', 'slug': 'sales', 'url': 'https://n8n.io/workflows/categories/sales/'},
                            {'name': 'IT Ops', 'slug': 'it-ops', 'url': 'https://n8n.io/workflows/categories/it-ops/'},
                            {'name': 'Marketing', 'slug': 'marketing', 'url': 'https://n8n.io/workflows/categories/marketing/'},
                            {'name': 'Document Ops', 'slug': 'document-ops', 'url': 'https://n8n.io/workflows/categories/document-ops/'},
                            {'name': 'Other', 'slug': 'other', 'url': 'https://n8n.io/workflows/categories/other/'},
                            {'name': 'Support', 'slug': 'support', 'url': 'https://n8n.io/workflows/categories/support/'}
                        ]
                        self.log(f"📋 CATEGORÍAS PRINCIPALES (FALLBACK): {len(known_categories)}")
                        for cat in known_categories:
                            self.log(f"  • {cat['name']} → {cat['url']}")
                        return known_categories
                    else:
                        self.log(f"⚠️ Intento {attempt + 1} falló, reintentando en 5 segundos...", "WARNING")
                        time.sleep(5)
            
            self.accept_all_cookies(page)
            
            categories = []
            
            # Buscar los botones de categorías cerca de la barra de búsqueda
            category_selectors = [
                "link[href*='/workflows/categories/']",
                "a[href*='/workflows/categories/']",
                ".category-link",
                "[data-category]"
            ]
            
            # Estrategia: Buscar enlaces que contengan '/workflows/categories/'
            for selector in category_selectors:
                elements = page.query_selector_all(selector)
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        text = element.inner_text().strip()
                        
                        if href and '/workflows/categories/' in href and text:
                            # Construir URL completa
                            full_url = urljoin(self.BASE_URL, href)
                            
                            # Extraer nombre de categoría de la URL
                            category_name = href.split('/workflows/categories/')[-1].rstrip('/')
                            
                            category_info = {
                                'name': text,
                                'slug': category_name,
                                'url': full_url
                            }
                            
                            # Evitar duplicados
                            if category_info not in categories:
                                categories.append(category_info)
                                
                    except Exception as e:
                        self.log(f"Error procesando elemento de categoría: {e}", "DEBUG")
            
            # FILTRAR AI de las categorías encontradas (ya fue procesada completamente)
            original_count = len(categories)
            categories = [cat for cat in categories if cat['slug'].lower() != 'ai']
            if len(categories) < original_count:
                self.log("🚫 Categoría AI EXCLUIDA (ya fue procesada completamente anteriormente)")
            
            # Si no encontramos por selectores, usar las conocidas (SIN AI)
            if not categories:
                self.log("⚠️ No se encontraron categorías automáticamente, usando lista conocida (SIN AI)")
                known_categories = [
                    {'name': 'Sales', 'slug': 'sales', 'url': 'https://n8n.io/workflows/categories/sales/'},
                    {'name': 'IT Ops', 'slug': 'it-ops', 'url': 'https://n8n.io/workflows/categories/it-ops/'},
                    {'name': 'Marketing', 'slug': 'marketing', 'url': 'https://n8n.io/workflows/categories/marketing/'},
                    {'name': 'Document Ops', 'slug': 'document-ops', 'url': 'https://n8n.io/workflows/categories/document-ops/'},
                    {'name': 'Other', 'slug': 'other', 'url': 'https://n8n.io/workflows/categories/other/'},
                    {'name': 'Support', 'slug': 'support', 'url': 'https://n8n.io/workflows/categories/support/'}
                ]
                categories = known_categories
            
            self.log(f"📋 CATEGORÍAS PRINCIPALES ENCONTRADAS: {len(categories)}")
            for cat in categories:
                self.log(f"  • {cat['name']} → {cat['url']}")
            
            return categories
            
        except Exception as e:
            self.log(f"Error descubriendo categorías principales: {e}", "ERROR")
            return []

    def discover_subcategories(self, page: Page, category: Dict[str, str]) -> List[Dict[str, str]]:
        """Descubre subcategorías usando datos hardcodeados obtenidos de investigación MCP"""
        self.log_category(category['name'], f"🔍 Obteniendo subcategorías hardcodeadas...")
        
        # SUBCATEGORÍAS HARDCODEADAS basadas en investigación exhaustiva con MCP Playwright
        # Datos obtenidos de análisis JavaScript DOM en cada categoría principal
        
        known_subcategories = {
            'sales': [
                {'name': 'CRM', 'slug': 'crm', 'url': 'https://n8n.io/workflows/categories/crm/'},
                {'name': 'Lead Generation', 'slug': 'lead-generation', 'url': 'https://n8n.io/workflows/categories/lead-generation/'},
                {'name': 'Lead Nurturing', 'slug': 'lead-nurturing', 'url': 'https://n8n.io/workflows/categories/lead-nurturing/'}
            ],
            'marketing': [
                {'name': 'Content Creation', 'slug': 'content-creation', 'url': 'https://n8n.io/workflows/categories/content-creation/'},
                {'name': 'Market Research', 'slug': 'market-research', 'url': 'https://n8n.io/workflows/categories/market-research/'},
                {'name': 'Social Media', 'slug': 'social-media', 'url': 'https://n8n.io/workflows/categories/social-media/'}
            ],
            'it-ops': [
                {'name': 'SecOps', 'slug': 'secops', 'url': 'https://n8n.io/workflows/categories/secops/'},
                {'name': 'Engineering', 'slug': 'engineering', 'url': 'https://n8n.io/workflows/categories/engineering/'},
                {'name': 'DevOps', 'slug': 'devops', 'url': 'https://n8n.io/workflows/categories/devops/'}
            ],
            'document-ops': [
                {'name': 'Document Extraction', 'slug': 'document-extraction', 'url': 'https://n8n.io/workflows/categories/document-extraction/'},
                {'name': 'File Management', 'slug': 'file-management', 'url': 'https://n8n.io/workflows/categories/file-management/'},
                {'name': 'Invoice Processing', 'slug': 'invoice-processing', 'url': 'https://n8n.io/workflows/categories/invoice-processing/'}
            ],
            'support': [
                {'name': 'Support Chatbot', 'slug': 'support-chatbot', 'url': 'https://n8n.io/workflows/categories/support-chatbot/'},
                {'name': 'Ticket Management', 'slug': 'ticket-management', 'url': 'https://n8n.io/workflows/categories/ticket-management/'},
                {'name': 'Internal Wiki', 'slug': 'internal-wiki', 'url': 'https://n8n.io/workflows/categories/internal-wiki/'}
            ],
            'other': [
                {'name': 'Crypto Trading', 'slug': 'crypto-trading', 'url': 'https://n8n.io/workflows/categories/crypto-trading/'},
                {'name': 'HR', 'slug': 'hr', 'url': 'https://n8n.io/workflows/categories/hr/'},
                {'name': 'Miscellaneous', 'slug': 'miscellaneous', 'url': 'https://n8n.io/workflows/categories/miscellaneous/'},
                {'name': 'Personal Productivity', 'slug': 'personal-productivity', 'url': 'https://n8n.io/workflows/categories/personal-productivity/'},
                {'name': 'Project Management', 'slug': 'project-management', 'url': 'https://n8n.io/workflows/categories/project-management/'}
            ]
        }
        
        category_slug = category['slug'].lower()
        
        if category_slug in known_subcategories:
            subcategories = []
            for subcat_data in known_subcategories[category_slug]:
                subcategory_info = {
                    'name': subcat_data['name'],
                    'slug': subcat_data['slug'],
                    'url': subcat_data['url'],
                    'parent': category['slug']
                }
                subcategories.append(subcategory_info)
            
            self.log_category(category['name'], f"📋 Subcategorías hardcodeadas: {len(subcategories)}")
            for subcat in subcategories:
                self.log_category(category['name'], f"  • {subcat['name']} → {subcat['url']}")
            
            return subcategories
        else:
            self.log_category(category['name'], "ℹ️ No tiene subcategorías conocidas, se procesará directamente")
            return []

    def extract_workflow_links(self, page: Page, category_name: str = "Unknown") -> List[Dict[str, Any]]:
        """Extrae links de workflows de la página actual"""
        workflows = []
        
        try:
            # Esperar a que se carguen los workflows (reducido)
            page.wait_for_timeout(1500)  # Reducido de 2000 a 1500ms
            
            # Buscar enlaces de workflows
            workflow_selectors = [
                "a[href*='/workflows/']",
                "link[href*='/workflows/']",
                "[data-workflow-id]"
            ]
            
            for selector in workflow_selectors:
                elements = page.query_selector_all(selector)
                
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        
                        # Verificar que es un workflow individual (no una categoría)
                        if (href and '/workflows/' in href and 
                            '/workflows/categories/' not in href and
                            re.search(r'/workflows/\d+', href)):
                            
                            # Extraer información del workflow
                            title_element = element.query_selector('h3, .workflow-title, [class*="title"]')
                            title = title_element.inner_text().strip() if title_element else "Unknown Title"
                            
                            # Generar slug del workflow
                            slug_match = re.search(r'/workflows/(\d+-[^/]+)', href)
                            slug = slug_match.group(1) if slug_match else f"workflow-{len(workflows)}"
                            
                            full_url = urljoin(self.BASE_URL, href)
                            
                            # NUEVO SISTEMA DE CONTEO MEJORADO (V3.1) - INVESTIGACIÓN CON MCP PLAYWRIGHT
                            # Basado en investigación DOM de n8n.io: nodos visibles + indicador +X = total nodos
                            nodes_count = 0
                            visible_nodes = 0
                            plus_indicator = 0
                            
                            # MÉTODO 1: Buscar el contenedor de nodos (lista ul)
                            node_list = element.query_selector('ul')
                            if node_list:
                                # Contar nodos visibles (li con tooltip)
                                visible_node_elements = node_list.query_selector_all('li:has([role="tooltip"])')
                                visible_nodes = len(visible_node_elements)
                                
                                # Buscar indicador +X (li con span que no tiene role)
                                plus_elements = node_list.query_selector_all('li span:not([role])')
                                for plus_element in plus_elements:
                                    plus_text = plus_element.inner_text().strip()
                                    plus_match = re.search(r'\+(\d+)', plus_text)
                                    if plus_match:
                                        plus_indicator = int(plus_match.group(1))
                                        break
                                
                                # CÁLCULO CORRECTO: visible + plus_indicator
                                nodes_count = visible_nodes + plus_indicator
                                
                                if nodes_count > 0:
                                    self.log_category(category_name, f"  📊 CONTEO MEJORADO para '{title[:30]}': {visible_nodes} visibles + {plus_indicator} adicionales = {nodes_count} total", "DEBUG")
                            
                            # MÉTODO 2: Fallback - buscar solo indicador +X (método anterior)
                            if nodes_count == 0:
                                element_text = element.inner_text()
                                plus_matches = re.findall(r'\+(\d+)', element_text)
                                if plus_matches:
                                    try:
                                        plus_indicator = int(plus_matches[0])
                                        # Sin nodos visibles detectados, usar solo el indicador
                                        # (esto puede subestimar el total real)
                                        nodes_count = plus_indicator
                                        self.log_category(category_name, f"  📊 FALLBACK - Solo +{plus_indicator} detectado para '{title[:30]}' (puede ser subestimación)", "DEBUG")
                                    except:
                                        pass
                            
                            # MÉTODO 3: Fallback adicional - buscar otros patrones comunes
                            if nodes_count == 0:
                                node_text_patterns = [
                                    r'(\d+)\s*nodes?',  # "5 nodes" o "5 node"
                                    r'(\d+)\s*nodos?',  # "5 nodos" o "5 nodo"
                                ]
                                
                                element_text = element.inner_text().lower()
                                for pattern in node_text_patterns:
                                    match = re.search(pattern, element_text, re.IGNORECASE)
                                    if match:
                                        try:
                                            nodes_count = int(match.group(1))
                                            self.log_category(category_name, f"  📊 Nodos detectados via patrón texto: {nodes_count} para '{title[:30]}'", "DEBUG")
                                            break
                                        except:
                                            continue
                            
                            # Si aún no tenemos conteo, registrar para debugging
                            if nodes_count == 0:
                                self.log_category(category_name, f"  ⚠️ No se pudo detectar nodos para '{title[:30]}' - OMITIENDO (puede necesitar revisión manual)", "DEBUG")
                            
                            # FILTRO DE PRECIO: Verificar que no tenga precio (debe ser gratuito)
                            has_price = False
                            is_free = False
                            
                            # Buscar indicadores de precio ($X, €X, etc.)
                            price_selectors = [
                                'font[dir="auto"][style*="vertical-align: inherit;"]',  # Selector específico para precios
                                'font:has-text("$")',
                                'span:has-text("$")',
                                'div:has-text("$")'
                            ]
                            
                            for price_selector in price_selectors:
                                price_element = element.query_selector(price_selector)
                                if price_element:
                                    price_text = price_element.inner_text().strip()
                                    if '$' in price_text or '€' in price_text or '£' in price_text:
                                        has_price = True
                                        self.log_category(category_name, f"  💰 PRECIO DETECTADO: {price_text} para '{title[:30]}' - RECHAZANDO", "DEBUG")
                                        break
                            
                            # Buscar indicador de gratuidad
                            free_selectors = [
                                'span:has-text("Free")',
                                'div:has-text("Free")',
                                'span:has-text("free")',
                                'div:has-text("free")'
                            ]
                            
                            for free_selector in free_selectors:
                                free_element = element.query_selector(free_selector)
                                if free_element:
                                    free_text = free_element.inner_text().strip().lower()
                                    if 'free' in free_text:
                                        is_free = True
                                        self.log_category(category_name, f"  🆓 GRATUITO CONFIRMADO para '{title[:30]}'", "DEBUG")
                                        break
                            
                            workflow_data = {
                                'title': title,
                                'slug': slug,
                                'url': full_url,
                                'nodes': nodes_count,
                                'category': category_name,
                                'has_price': has_price,
                                'is_free': is_free
                            }
                            
                            # FILTROS COMBINADOS: nodos >= MIN_NODES AND sin precio AND debe ser gratuito
                            if (nodes_count > 0 and 
                                nodes_count >= self.MIN_NODES and 
                                not has_price and 
                                is_free and 
                                workflow_data not in workflows):
                                workflows.append(workflow_data)
                                self.log_category(category_name, f"  ✅ ACEPTADO: {title[:40]}... ({nodes_count} nodos, GRATUITO)", "DEBUG")
                            else:
                                if nodes_count == 0:
                                    self.log_category(category_name, f"  ❌ OMITIDO - Sin info de nodos: {title[:40]}...", "DEBUG")
                                elif nodes_count < self.MIN_NODES:
                                    self.log_category(category_name, f"  ❌ RECHAZADO - Pocos nodos: {title[:40]}... ({nodes_count} nodos)", "DEBUG")
                                elif has_price:
                                    self.log_category(category_name, f"  ❌ RECHAZADO - Tiene precio: {title[:40]}...", "DEBUG")
                                elif not is_free:
                                    self.log_category(category_name, f"  ❌ RECHAZADO - No es gratuito: {title[:40]}...", "DEBUG")
                                
                    except Exception as e:
                        self.log(f"Error procesando workflow: {e}", "DEBUG")
            
            self.log_category(category_name, f"Workflows válidos encontrados: {len(workflows)}")
            
        except Exception as e:
            self.log_category(category_name, f"Error extrayendo workflows: {e}", "ERROR")
        
        return workflows

    def load_more_pages(self, page: Page, category_name: str = "Unknown") -> bool:
        """Carga más páginas si está disponible el botón 'Load more templates'"""
        try:
            load_more_button = page.query_selector("text=Load more templates")
            
            if load_more_button and load_more_button.is_visible():
                self.log_category(category_name, "📄 Cargando más templates...")
                load_more_button.click()
                page.wait_for_timeout(2000)  # Reducido de 3000 a 2000ms
                return True
            else:
                self.log_category(category_name, "No hay más páginas para cargar")
                return False
                
        except Exception as e:
            self.log_category(category_name, f"Error cargando más páginas: {e}", "ERROR")
            return False

    def download_workflow_via_clipboard(self, page: Page, workflow: Dict[str, Any]) -> bool:
        """Descarga workflow usando el método de portapapeles"""
        category_dir = self.download_dir / workflow['category']
        category_dir.mkdir(exist_ok=True)
        
        file_path = category_dir / f"{workflow['slug']}.json"
        
        if file_path.exists():
            self.log_category(workflow['category'], f"Ya existe: {workflow['slug']} - omitiendo")
            return True
        
        try:
            self.log_category(workflow['category'], f"🌐 Navegando a: {workflow['url']}")
            page.goto(workflow['url'], wait_until="networkidle", timeout=self.TIMEOUT)
            page.wait_for_timeout(2000)  # Reducido de 3000 a 2000ms
            
            if "n8n.io" not in page.url:
                self.log_category(workflow['category'], f"❌ La página no se cargó correctamente: {page.url}")
                return False
            
            # Buscar y hacer clic en "Use for free"
            use_button = page.query_selector("button:has-text('Use for free')")
            if use_button and use_button.is_visible():
                use_button.click()
                page.wait_for_timeout(2500)  # Reducido de 4000 a 2500ms
                
                copy_selectors = [
                    'div.cursor-pointer:has-text("Copy template to clipboard (JSON)")',
                    'div:has-text("Copy template to clipboard (JSON)")',
                    'button:has-text("Copy template to clipboard")',
                    '[data-testid="copy-template"]'
                ]
                
                copy_clicked = False
                for selector in copy_selectors:
                    copy_button = page.query_selector(selector)
                    if copy_button and copy_button.is_visible():
                        copy_button.click()
                        page.wait_for_timeout(800)  # Reducido de 1000 a 800ms
                        copy_clicked = True
                        break
                
                if copy_clicked:
                    clipboard_content = page.evaluate("""
                        () => {
                            return navigator.clipboard.readText().then(text => {
                                return text;
                            }).catch(error => {
                                return null;
                            });
                        }
                    """)
                    
                    if clipboard_content:
                        try:
                            workflow_data = json.loads(clipboard_content)
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                            
                            return True
                            
                        except json.JSONDecodeError:
                            self.log_category(workflow['category'], f"❌ JSON inválido para {workflow['slug']}")
                            return False
                    else:
                        self.log_category(workflow['category'], f"❌ No se pudo leer portapapeles para {workflow['slug']}")
                        return False
                else:
                    self.log_category(workflow['category'], f"❌ No se encontró botón de copia para {workflow['slug']}")
                    return False
            else:
                self.log_category(workflow['category'], f"❌ No se encontró botón 'Use for free' para {workflow['slug']}")
                return False
                
        except Exception as e:
            self.log_category(workflow['category'], f"❌ Error descargando {workflow['slug']}: {e}")
            return False

    def download_batch_immediately(self, context: BrowserContext, workflows: List[Dict[str, Any]], category_name: str) -> None:
        """Descarga inmediata de un lote de workflows"""
        if not workflows:
            return
            
        self.log_category(category_name, f"⚡ DESCARGA INMEDIATA: {len(workflows)} workflows")
        
        batch_size = min(3, len(workflows))
        tabs = []
        
        try:
            for i in range(batch_size):
                tab = context.new_page()
                tabs.append(tab)
                time.sleep(0.5)  # Aumentado de 0.3s a 0.5s para estabilidad
                self.log_category(category_name, f"📄 Pestaña {i+1}/{batch_size} creada")
            
            successes = 0
            for i, workflow in enumerate(workflows):
                tab_index = i % batch_size
                self.log_category(category_name, f"  ⬇️ [{i+1}/{len(workflows)}] Descargando: {workflow['title']}")
                
                if self.download_workflow_via_clipboard(tabs[tab_index], workflow):
                    successes += 1
                    self.global_stats['total_workflows_downloaded'] += 1
                    if category_name not in self.category_stats:
                        self.category_stats[category_name] = {'downloaded': 0, 'errors': 0, 'found': 0}
                    self.category_stats[category_name]['downloaded'] += 1
                    self.log_category(category_name, f"  ✅ ÉXITO: {workflow['slug']}")
                else:
                    self.global_stats['total_errors'] += 1
                    if category_name not in self.category_stats:
                        self.category_stats[category_name] = {'downloaded': 0, 'errors': 0, 'found': 0}
                    self.category_stats[category_name]['errors'] += 1
                    self.log_category(category_name, f"  ❌ FALLO: {workflow['slug']}")
                    
                time.sleep(1.0)  # Aumentado de 0.7s a 1.0s para evitar errores
                    
        finally:
            for tab in tabs:
                try:
                    tab.close()
                except:
                    pass
            self.log_category(category_name, f"⚡ Descarga inmediata completada: {successes}/{len(workflows)} exitosas")

    def scrape_category_workflows(self, context: BrowserContext, category: Dict[str, str], exploration_page: Page = None) -> None:
        """Scraping completo de todos los workflows de una categoría/subcategoría"""
        category_name = category['name']
        self.log_category(category_name, f"🚀 INICIANDO SCRAPING COMPLETO")
        
        # Inicializar estadísticas de categoría
        if category_name not in self.category_stats:
            self.category_stats[category_name] = {'downloaded': 0, 'errors': 0, 'found': 0}
        
        # Usar la página de exploración reutilizable si se proporciona, sino crear nueva
        page = exploration_page if exploration_page else context.new_page()
        
        try:
            # Construir URL con parámetros
            category_url = f"{category['url']}?count={self.WORKFLOWS_PER_PAGE}"
            self.log_category(category_name, f"🌐 Navegando a: {category_url}")
            
            page.goto(category_url, wait_until="networkidle", timeout=self.TIMEOUT)
            page.wait_for_timeout(3000)
            
            all_workflows = []
            processed_slugs = set()
            pages_loaded = 0
            pending_downloads = []
            
            while True:
                pages_loaded += 1
                self.log_category(category_name, f"📄 Procesando página {pages_loaded}")
                
                # Extraer workflows de la página actual
                page_workflows = self.extract_workflow_links(page, category_name)
                
                new_workflows = 0
                for workflow in page_workflows:
                    if (workflow['slug'] not in processed_slugs and 
                        len(all_workflows) < self.MAX_WORKFLOWS_PER_SUBCATEGORY):
                        processed_slugs.add(workflow['slug'])
                        all_workflows.append(workflow)
                        pending_downloads.append(workflow)
                        new_workflows += 1
                        self.global_stats['total_workflows_found'] += 1
                        self.category_stats[category_name]['found'] += 1
                        
                        # Verificar si alcanzamos el límite
                        if len(all_workflows) >= self.MAX_WORKFLOWS_PER_SUBCATEGORY:
                            self.log_category(category_name, f"🎯 LÍMITE ALCANZADO: {self.MAX_WORKFLOWS_PER_SUBCATEGORY} workflows")
                            break
                
                self.log_category(category_name, f"📊 Nuevos: {new_workflows} | Total: {len(all_workflows)}/{self.MAX_WORKFLOWS_PER_SUBCATEGORY}")
                
                # Verificar si ya alcanzamos el límite
                if len(all_workflows) >= self.MAX_WORKFLOWS_PER_SUBCATEGORY:
                    break
                
                # Descarga inmediata cada X workflows
                if len(pending_downloads) >= self.DOWNLOAD_BATCH_SIZE:
                    self.log_category(category_name, f"🚀 DESCARGA INMEDIATA: {len(pending_downloads)} workflows acumulados")
                    self.download_batch_immediately(context, pending_downloads, category_name)
                    pending_downloads = []
                
                # Intentar cargar más páginas
                if not self.load_more_pages(page, category_name):
                    self.log_category(category_name, "🏁 No hay más páginas disponibles")
                    break
                
                # Límite de seguridad para evitar bucles infinitos
                if pages_loaded > 30:  # Reducido de 50 a 30
                    self.log_category(category_name, "⚠️ Límite de páginas alcanzado (30), finalizando")
                    break
            
            # Descargar workflows restantes
            if pending_downloads:
                self.log_category(category_name, f"🔚 DESCARGA FINAL: {len(pending_downloads)} workflows restantes")
                self.download_batch_immediately(context, pending_downloads, category_name)
            
            # Mensaje final con razón de terminación
            if len(all_workflows) >= self.MAX_WORKFLOWS_PER_SUBCATEGORY:
                self.log_category(category_name, f"✅ SCRAPING COMPLETADO - LÍMITE ALCANZADO: {len(all_workflows)} workflows")
            else:
                self.log_category(category_name, f"✅ SCRAPING COMPLETADO - Total encontrados: {len(all_workflows)} workflows")
            
        except Exception as e:
            self.log_category(category_name, f"❌ ERROR en scraping: {e}", "ERROR")
        finally:
            # Solo cerrar la página si no es la página de exploración reutilizable
            if not exploration_page:
                try:
                    page.close()
                except:
                    pass

    def print_final_statistics(self) -> None:
        """Imprime estadísticas finales completas"""
        duration = time.time() - self.global_stats['start_time']
        
        print("\n" + "="*80)
        print("🎉 SCRAPING MASIVO COMPLETADO - ESTADÍSTICAS FINALES")
        print("="*80)
        
        print(f"⏱️  Duración total: {duration:.2f} segundos ({duration/60:.1f} minutos)")
        print(f"📂 Categorías exploradas: {self.global_stats['categories_explored']}")
        print(f"📁 Subcategorías exploradas: {self.global_stats['subcategories_explored']}")
        print(f"🔍 Total workflows encontrados: {self.global_stats['total_workflows_found']}")
        print(f"⬇️  Total workflows descargados: {self.global_stats['total_workflows_downloaded']}")
        print(f"❌ Total errores: {self.global_stats['total_errors']}")
        
        if self.global_stats['total_workflows_found'] > 0:
            success_rate = (self.global_stats['total_workflows_downloaded'] / self.global_stats['total_workflows_found']) * 100
            print(f"✅ Tasa de éxito: {success_rate:.1f}%")
        
        print("\n📊 ESTADÍSTICAS POR CATEGORÍA:")
        print("-"*80)
        
        for category, stats in self.category_stats.items():
            found = stats.get('found', 0)
            downloaded = stats.get('downloaded', 0)
            errors = stats.get('errors', 0)
            rate = (downloaded / found * 100) if found > 0 else 0
            
            print(f"📁 {category:<20} | Encontrados: {found:>4} | Descargados: {downloaded:>4} | Errores: {errors:>3} | Éxito: {rate:>5.1f}%")
        
        print("\n💾 Archivos guardados en:")
        print(f"   {self.download_dir.absolute()}")
        
        print("\n🗂️  Estructura de directorios:")
        for category_dir in sorted(self.download_dir.iterdir()):
            if category_dir.is_dir():
                file_count = len(list(category_dir.glob('*.json')))
                print(f"   📁 {category_dir.name}/ ({file_count} archivos)")

    def scrape_all_categories_comprehensively(self) -> None:
        """Proceso principal: scraping masivo de todas las categorías y subcategorías"""
        self.log("🚀 INICIANDO N8N COMPREHENSIVE WORKFLOW SCRAPER V3.0")
        self.log("🌍 EXPLORACIÓN MASIVA DE TODAS LAS CATEGORÍAS")
        self.log(f"📁 Directorio de descarga: {self.download_dir.absolute()}")
        self.log(f"🔢 Mínimo de nodos requeridos: {self.MIN_NODES}")
        self.log(f"⚡ Descarga cada: {self.DOWNLOAD_BATCH_SIZE} workflows")
        self.log("="*80)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=self.SLOW_MO,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            
            try:
                # FASE 1: Descubrir todas las categorías principales
                self.log("🗺️  FASE 1: Descubriendo categorías principales...")
                main_categories = self.discover_main_categories(page)
                
                if not main_categories:
                    self.log("❌ No se pudieron descubrir categorías principales", "ERROR")
                    return
                
                self.global_stats['categories_explored'] = len(main_categories)
                
                # FASE 2: Para cada categoría principal, explorar subcategorías y scrape
                for i, category in enumerate(main_categories):
                    self.log(f"\n🎯 [{i+1}/{len(main_categories)}] PROCESANDO CATEGORÍA: {category['name']}")
                    
                    # Buscar subcategorías
                    subcategories = self.discover_subcategories(page, category)
                    
                    if subcategories:
                        # Tiene subcategorías - procesarlas individualmente
                        self.global_stats['subcategories_explored'] += len(subcategories)
                        
                        for j, subcat in enumerate(subcategories):
                            self.log(f"  📂 [{j+1}/{len(subcategories)}] Subcategoría: {subcat['name']}")
                            self.scrape_category_workflows(context, subcat, page)  # Reutilizar la misma pestaña
                            
                            # Pausa pequeña entre subcategorías
                            if j < len(subcategories) - 1:
                                self.log(f"⏳ Pausa de 3 segundos antes de la siguiente subcategoría...")
                                time.sleep(3)
                    else:
                        # No tiene subcategorías - procesar la categoría directamente
                        self.scrape_category_workflows(context, category, page)  # Reutilizar la misma pestaña
                    
                    # Pausa entre categorías principales (reducida)
                    if i < len(main_categories) - 1:
                        self.log("⏳ Pausa de 5 segundos antes de la siguiente categoría...")
                        time.sleep(5)  # Reducido de 10 a 5 segundos
                
                # FASE 3: Estadísticas finales
                self.print_final_statistics()
                
            except Exception as e:
                self.log(f"❌ ERROR CRÍTICO en scraping masivo: {e}", "ERROR")
            finally:
                try:
                    browser.close()
                except:
                    pass


def main():
    scraper = N8NComprehensiveWorkflowScraper()
    scraper.scrape_all_categories_comprehensively()


if __name__ == "__main__":
    main()