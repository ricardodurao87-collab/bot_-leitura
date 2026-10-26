import time
import random
import asyncio
import urllib.request
import concurrent.futures
import subprocess
import os
import sys

# Garante que os logs apareçam em tempo real no GitHub Actions / Nuvem
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# No Windows (.EXE), salva o navegador em pasta fixa; no Linux (GitHub Actions), usa o padrão do sistema
if sys.platform == "win32":
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "NavegadoresBotLivraria"
    )

from playwright.async_api import async_playwright

# ==============================================================================
# CONFIGURAÇÕES DE ALTA ESCALA E RENDIMENTO (OTIMIZADO PARA GOOGLE ANALYTICS 4)
# ==============================================================================
IS_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"
QTD_BOTS = int(os.environ.get("QTD_BOTS", 25 if IS_GITHUB else 35))
QTD_NAVEGADORES_BASE = int(os.environ.get("QTD_NAVEGADORES_BASE", 4 if IS_GITHUB else 5))
TEMPO_LEITURA_MIN = 16        # Tempo mínimo lendo cada matéria (GA4 exige >10s p/ sessão engajada)
TEMPO_LEITURA_MAX = 30        # Tempo máximo lendo cada matéria (em segundos)
ARTIGOS_POR_CICLO_MIN = 2     # Qtd mínima de notícias lidas por ciclo
ARTIGOS_POR_CICLO_MAX = 4     # Qtd máxima de notícias lidas por ciclo
ESPERA_SUCESSO_MIN = 3        # Espera mínima após concluir ciclo com sucesso (em segundos)
ESPERA_SUCESSO_MAX = 8         # Espera máxima após concluir ciclo com sucesso (em segundos)
TIMEOUT_CONEXAO_PROXY = 22000 # Timeout rápido (22s) para descartar proxy lento sem travar o bot
TIMEOUT_PAGINA = 32000        # Timeout de carregamento de artigos (em milissegundos)
MODO_INVISIVEL = True         # True = Segundo plano oculto | False = Mostra janela
# ==============================================================================

# Proxies HTTPS pré-verificados diretamente contra https://plantaocnp.com/
SEED_PROXIES_PLANTAOCNP = [
    "45.139.85.2:3128", "200.59.186.55:999", "195.154.191.26:1092",
    "45.65.224.74:999", "160.22.45.66:8080", "38.210.160.159:8080",
    "45.125.64.215:443", "185.246.155.83:8080", "103.187.162.221:8282",
    "112.169.99.71:8059", "112.169.99.71:8071", "203.252.142.217:80",
    "162.43.106.22:60000", "45.198.10.39:9191", "182.53.202.217:80",
    "122.246.3.12:17981", "170.254.228.90:999", "49.149.89.202:8080",
    "43.224.188.142:8080", "148.230.212.70:8080", "171.241.15.131:32650",
    "1.20.101.35:80", "49.149.174.69:8082", "200.70.35.2:8080",
    "112.65.132.181:3128", "203.205.49.2:10170", "92.62.149.82:8080",
    "187.190.58.152:8081", "220.135.222.226:3128", "192.147.114.47:1111",
    "103.41.97.225:83", "31.223.16.134:8888", "49.151.176.241:8082",
    "78.9.234.55:8080", "194.87.244.192:80", "160.22.198.19:8082",
    "201.4.69.178:8080", "103.125.15.60:3128", "41.159.154.43:3128",
    "200.125.170.218:999", "103.25.195.69:8181", "45.174.56.21:999",
    "103.111.116.233:81", "103.136.107.60:100", "103.160.68.215:8080",
    "170.245.132.85:999", "165.101.43.155:8080", "116.203.139.209:5678",
    "200.116.198.222:9812", "103.178.160.149:3128", "78.17.144.104:18080",
    "104.219.55.50:8118", "66.175.219.29:3128", "205.164.46.6:3182",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "124", "124.0.6367.118", "Windows", "15.0.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "125", "125.0.6422.141", "Windows", "15.0.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "126", "126.0.6478.126", "Windows", "10.0.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "127", "127.0.6533.99", "Windows", "15.0.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "128", "128.0.6613.84", "Windows", "15.0.0"
    ),
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
]

# Domínios de Analytics/Stats que NUNCA podem ser bloqueados
DOMINIOS_ANALYTICS_PERMITIDOS = (
    "google-analytics.com",
    "analytics.google.com",
    "googletagmanager.com",
    "stats.wp.com",
    "pixel.wp.com",
    "g/collect",
    "g.gif",
    "google.com",
    "gstatic.com",
)

# Domínios pesados para bloquear (ex: vídeo autoplay do YouTube na Home que trava proxies gratuitos)
DOMINIOS_PESADOS_BLOQUEADOS = (
    "youtube.com/embed",
    "googlevideo.com",
    "ytimg.com",
)


def build_stealth_script(major_ver: str, full_ver: str, platform: str, platform_ver: str) -> str:
    """Remove a assinatura HeadlessChrome do navigator.userAgentData e oculta o navigator.webdriver."""
    return f"""
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    window.chrome = {{ runtime: {{}} }};
    Object.defineProperty(navigator, 'languages', {{ get: () => ['pt-BR', 'pt', 'en-US', 'en'] }});
    Object.defineProperty(navigator, 'plugins', {{ get: () => [1, 2, 3, 4, 5] }});
    Object.defineProperty(document, 'visibilityState', {{ get: () => 'visible' }});
    Object.defineProperty(document, 'hidden', {{ get: () => false }});

    if (navigator.userAgentData) {{
        const brands = [
            {{ brand: 'Not:A-Brand', version: '99' }},
            {{ brand: 'Google Chrome', version: '{major_ver}' }},
            {{ brand: 'Chromium', version: '{major_ver}' }}
        ];
        const fullVersionList = [
            {{ brand: 'Not:A-Brand', version: '99.0.0.0' }},
            {{ brand: 'Google Chrome', version: '{full_ver}' }},
            {{ brand: 'Chromium', version: '{full_ver}' }}
        ];
        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => ({{
                brands: brands,
                mobile: false,
                platform: '{platform}',
                getHighEntropyValues: async (hints) => ({{
                    architecture: 'x86',
                    bitness: '64',
                    brands: brands,
                    fullVersionList: fullVersionList,
                    mobile: false,
                    model: '',
                    platform: '{platform}',
                    platformVersion: '{platform_ver}',
                    uaFullVersion: '{full_ver}',
                    wow64: false
                }}),
                toJSON: () => ({{ brands: brands, mobile: false, platform: '{platform}' }})
            }})
        }});
    }}
    """


def auto_install_chromium():
    print("[*] Sincronizando e preparando o motor do navegador (aguarde na 1ª vez)...")
    try:
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        executable, cli = compute_driver_executable()
        env = get_driver_env()
        subprocess.run([str(executable), str(cli), "install", "chromium"], env=env, check=False)
    except Exception:
        pass


def check_proxy_plantaocnp(proxy):
    """
    Testa o proxy DIRETAMENTE contra https://plantaocnp.com/robots.txt!
    Garante que o proxy:
    1) Suporta HTTPS (TLS/SSL CONNECT)
    2) NÃO está bloqueado pelo firewall do plantaocnp.com
    3) Responde rápido (< 4.5 segundos)
    """
    url = "https://plantaocnp.com/robots.txt"
    p_url = f"http://{proxy}" if "://" not in proxy else proxy
    proxy_handler = urllib.request.ProxyHandler({'http': p_url, 'https': p_url})

    opener = urllib.request.build_opener(proxy_handler)
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    ]

    start = time.time()
    try:
        resp = opener.open(url, timeout=4.5)
        if resp.getcode() == 200:
            body = resp.read(256).decode('utf-8', errors='ignore')
            if "YOAST" in body or "plantaocnp.com" in body:
                return proxy, time.time() - start
    except Exception:
        pass
    return proxy, float('inf')


class ProxyManager:
    """
    Gerenciador inteligente de proxies com:
    - Validação direta no servidor https://plantaocnp.com/
    - Pool Ouro (golden_proxies): reaproveita proxies que comprovaram funcionar na navegação real
    - Lista Negra (bad_proxies): bane imediatamente proxies que deram timeout
    """
    def __init__(self):
        self.valid_proxies = []
        self.golden_proxies = []
        self.bad_proxies = set()
        self.tested_candidates = set()
        self.fetching = False
        self.lock = asyncio.Lock()
        self.last_fetch_time = 0

    async def get_proxy(self):
        async with self.lock:
            if (len(self.valid_proxies) < 18 or (time.time() - self.last_fetch_time) > 180) and not self.fetching:
                asyncio.create_task(self.refresh_proxies())

            # 1º Prioridade: proxies novos validados na fila
            while self.valid_proxies:
                px = self.valid_proxies.pop(0)
                if px not in self.bad_proxies:
                    return px

            # 2º Prioridade: proxies do Pool Ouro (já validados em ciclos anteriores com sucesso)
            if self.golden_proxies:
                px = self.golden_proxies.pop(0)
                self.golden_proxies.append(px)  # Rotaciona no fim da fila
                return px

        # Aguarda brevemente caso a busca inicial ainda esteja rodando
        for _ in range(16):
            await asyncio.sleep(0.5)
            async with self.lock:
                while self.valid_proxies:
                    px = self.valid_proxies.pop(0)
                    if px not in self.bad_proxies:
                        return px
                if self.golden_proxies:
                    px = self.golden_proxies.pop(0)
                    self.golden_proxies.append(px)
                    return px

        return None

    async def report_success(self, proxy_str):
        """Promove o proxy que completou leitura real ao Pool Ouro para reuso."""
        if not proxy_str:
            return
        async with self.lock:
            self.bad_proxies.discard(proxy_str)
            if proxy_str not in self.golden_proxies:
                self.golden_proxies.append(proxy_str)

    async def report_failure(self, proxy_str):
        """Remove imediatamente o proxy que deu ERR_TIMED_OUT para não atrasar outros bots."""
        if not proxy_str:
            return
        async with self.lock:
            self.bad_proxies.add(proxy_str)
            if proxy_str in self.golden_proxies:
                self.golden_proxies.remove(proxy_str)
            if proxy_str in self.valid_proxies:
                self.valid_proxies.remove(proxy_str)

    async def refresh_proxies(self):
        async with self.lock:
            if self.fetching:
                return
            self.fetching = True

        print("\n[ProxyManager] Escaneando proxies rápidos diretamente contra https://plantaocnp.com/...")

        sources = [
            "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&ssl=yes&proxy_format=ipport&format=text",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
        ]

        def fetch_and_test(already_tested, bad_set):
            # Na 1ª execução, testa imediatamente os SEED_PROXIES_PLANTAOCNP + novos
            priority_candidates = [p for p in SEED_PROXIES_PLANTAOCNP if p not in bad_set]
            scraped = []

            for url in sources:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=6) as response:
                        content = response.read().decode('utf-8', errors='ignore')
                        for line in content.splitlines():
                            line = line.strip().split('://')[-1]
                            if ":" in line and not line.startswith("#"):
                                if not (line.startswith("47.") or line.startswith("8.2")):
                                    if line not in bad_set and line not in already_tested:
                                        scraped.append(line)
                except Exception:
                    pass

            random.shuffle(scraped)
            # Combina os seeds conhecidos com uma amostra de 350 novos IPs não testados
            amostra = list(dict.fromkeys(priority_candidates + scraped[:350]))
            if not amostra:
                return [], []

            print(f"[ProxyManager] Testando conexão real ao Plantão CNP em {len(amostra)} IPs simultaneamente (100 threads)...")

            tested = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                futures = {executor.submit(check_proxy_plantaocnp, p): p for p in amostra}
                for future in concurrent.futures.as_completed(futures):
                    px, spd = future.result()
                    if spd != float('inf'):
                        tested.append((px, spd))

            tested.sort(key=lambda x: x[1])
            return [x[0] for x in tested], amostra

        try:
            loop = asyncio.get_running_loop()
            async with self.lock:
                tested_snapshot = set(self.tested_candidates)
                bad_snapshot = set(self.bad_proxies)

            new_proxies, tested_batch = await loop.run_in_executor(
                None, fetch_and_test, tested_snapshot, bad_snapshot
            )

            async with self.lock:
                self.tested_candidates.update(tested_batch)
                if len(self.tested_candidates) > 5000:
                    self.tested_candidates.clear()

                current_set = set(self.valid_proxies)
                added_count = 0
                for p in new_proxies:
                    if p not in current_set and p not in self.bad_proxies:
                        self.valid_proxies.append(p)
                        if p not in self.golden_proxies:
                            self.golden_proxies.append(p)
                        added_count += 1
                print(
                    f"[ProxyManager] Concluído! +{added_count} IPs aprovados no Plantão CNP | "
                    f"Fila: {len(self.valid_proxies)} | Pool Ouro: {len(self.golden_proxies)}"
                )
                self.last_fetch_time = time.time()
        except Exception as e:
            print(f"[ProxyManager] Erro ao atualizar proxies: {e}")
        finally:
            self.fetching = False


proxy_manager = ProxyManager()


class BrowserPool:
    """
    Mantém um pool fixo de 5 instâncias do navegador Chromium compartilhadas entre os 35 bots.
    Cada bot cria seu próprio Contexto isolado (com seu próprio Proxy, Cookies _ga e User-Agent),
    evitando abrir 35 processos pesados que esgotam a rede e causam ERR_TIMED_OUT.
    """
    def __init__(self, playwright_instance, size=QTD_NAVEGADORES_BASE):
        self.p = playwright_instance
        self.size = size
        self.browsers = [None] * size
        self.locks = [asyncio.Lock() for _ in range(size)]

    async def get_browser(self, bot_id):
        idx = (bot_id - 1) % self.size
        async with self.locks[idx]:
            b = self.browsers[idx]
            if b is None or not b.is_connected():
                try:
                    if b:
                        await b.close()
                except Exception:
                    pass
                b = await self.p.chromium.launch(
                    headless=MODO_INVISIVEL,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-extensions',
                        '--mute-audio',
                        '--no-first-run',
                        '--disable-renderer-backgrounding',
                        '--disable-background-timer-throttling',
                    ]
                )
                self.browsers[idx] = b
            return b


async def get_article_links(page):
    links_js = """
    Array.from(document.querySelectorAll("a")).map(a => a.href).filter(href => {
        try {
            const urlObj = new URL(href, window.location.href);
            const path = urlObj.pathname;
            return (path.match(/-/g) || []).length >= 3 && urlObj.hostname.includes("plantaocnp.com");
        } catch(e) {
            return false;
        }
    })
    """
    try:
        hrefs = await page.evaluate(links_js)
        return list(dict.fromkeys(hrefs))
    except Exception:
        return []


async def get_home_logo_locator(page):
    locators = [
        "a.custom-logo-link",
        "a[rel='home']",
        "header a img",
        "a[title*='Home']",
        "a[href='https://plantaocnp.com/']",
        "a[href='https://www.plantaocnp.com/']",
        "a[href='/']"
    ]
    for loc in locators:
        try:
            element = page.locator(loc).first
            if await element.is_visible():
                return element
        except Exception:
            pass
    return None


async def slow_scroll(page, distance_px, duration_sec):
    steps = max(1, int(duration_sec * 12))
    step_distance = distance_px / steps

    for _ in range(steps):
        micro_dist = step_distance * random.uniform(0.8, 1.2)
        try:
            await page.evaluate(f"window.scrollBy({{top: {micro_dist}, left: 0, behavior: 'auto'}});")
            await asyncio.sleep(duration_sec / steps)
        except Exception:
            break


async def flush_analytics_events(page):
    """Força o envio imediato de pacotes em lote do GA4 antes de navegar ou fechar a aba."""
    try:
        await page.evaluate("""
            window.dispatchEvent(new Event('scroll'));
            window.dispatchEvent(new Event('blur'));
            document.dispatchEvent(new Event('visibilitychange'));
        """)
        await asyncio.sleep(1.2)
    except Exception:
        pass


async def simulate_human_engagement(page, duration_sec, scroll_speed_multiplier, scroll_distance_multiplier):
    start_time = time.time()
    print(f"      [Engajamento] Lendo matéria por {duration_sec:.0f}s (Sessão Engajada GA4)...")

    while (time.time() - start_time) < duration_sec:
        time_left = duration_sec - (time.time() - start_time)
        if time_left <= 0:
            break

        direction = 1 if random.random() < 0.85 else -1
        base_dist = random.randint(150, 350)
        dist = base_dist * scroll_distance_multiplier * direction

        base_scroll_time = random.uniform(1.0, 2.5)
        scroll_time = base_scroll_time * scroll_speed_multiplier

        try:
            current_scroll = await page.evaluate("window.scrollY")
            if direction == -1 and current_scroll < 200:
                direction = 1
                dist = random.randint(150, 300) * scroll_distance_multiplier

            if scroll_time > time_left:
                scroll_time = time_left

            if scroll_time > 0:
                await slow_scroll(page, dist, scroll_time)
        except Exception:
            break

        pause = random.uniform(1.5, 3.0) * scroll_speed_multiplier
        time_left = duration_sec - (time.time() - start_time)
        if pause > time_left:
            pause = max(0, time_left)

        if pause > 0:
            await asyncio.sleep(pause)


async def create_bot_context(browser, proxy_str, bot_id):
    """Cria um contexto isolado com camuflagem GA4 e bloqueio seletivo de mídia pesada."""
    ua_str, major_ver, full_ver, platform, platform_ver = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    proxy_config = {'server': f'http://{proxy_str}'} if proxy_str else None

    context = await browser.new_context(
        proxy=proxy_config,
        viewport=viewport,
        locale='pt-BR',
        timezone_id='America/Cuiaba',
        user_agent=ua_str,
        ignore_https_errors=True,
        extra_http_headers={
            'Sec-CH-UA': f'"Not:A-Brand";v="99", "Google Chrome";v="{major_ver}", "Chromium";v="{major_ver}"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': f'"{platform}"',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    )

    await context.add_init_script(build_stealth_script(major_ver, full_ver, platform, platform_ver))

    async def block_heavy_resources(route):
        url = route.request.url.lower()
        rtype = route.request.resource_type

        if any(allow in url for allow in DOMINIOS_ANALYTICS_PERMITIDOS):
            await route.continue_()
            return

        if any(block in url for block in DOMINIOS_PESADOS_BLOQUEADOS) or rtype in ["media", "font", "image"]:
            await route.abort()
        else:
            await route.continue_()

    await context.route("**/*", block_heavy_resources)
    return context


async def run_bot(bot_id, browser_pool: BrowserPool):
    # Escalonamento suave de partida para os 35 bots
    await asyncio.sleep((bot_id - 1) * 0.8)

    while True:
        browser = None
        try:
            browser = await browser_pool.get_browser(bot_id)
        except Exception as e:
            print(f"[BOT {bot_id}] [!] Reabrindo motor Chromium: {e}")
            await asyncio.sleep(3)
            continue

        # Sistema de Auto-Troca Rápida: tenta até 3 proxies antes de usar fallback direto,
        # eliminando as mensagens de erro "net::ERR_TIMED_OUT" no meio do ciclo!
        context = None
        page = None
        proxy_str = None
        ga_hits = 0
        wp_hits = 0
        home_loaded = False

        for tentativa in range(1, 4):
            proxy_str = await proxy_manager.get_proxy() if tentativa <= 2 else None
            try:
                context = await create_bot_context(browser, proxy_str, bot_id)
                page = await context.new_page()
                page.set_default_timeout(TIMEOUT_PAGINA)

                def on_response(res):
                    nonlocal ga_hits, wp_hits
                    r_url = res.url.lower()
                    if "google-analytics.com/g/collect" in r_url and res.status in (200, 204):
                        ga_hits += 1
                        print(f"[BOT {bot_id}] [✓ GA4] Visualização confirmada no Google Analytics (#{ga_hits})")
                    elif "pixel.wp.com/g.gif" in r_url and res.status == 200:
                        wp_hits += 1
                        print(f"[BOT {bot_id}] [✓ WP-STATS] Visualização confirmada no Jetpack (#{wp_hits})")

                page.on("response", on_response)

                origem_ip = f"Proxy {proxy_str}" if proxy_str else "Conexão Direta Rápida"
                print(f"[BOT {bot_id}] Abrindo plantaocnp.com via {origem_ip}...")

                await page.goto(
                    "https://plantaocnp.com/",
                    wait_until="domcontentloaded",
                    referer="https://www.google.com/",
                    timeout=TIMEOUT_CONEXAO_PROXY
                )
                home_loaded = True
                break
            except Exception:
                # Se o proxy falhou ou deu timeout na entrada, bane ele silenciosamente e já tenta o próximo
                if proxy_str:
                    await proxy_manager.report_failure(proxy_str)
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                context = None
                page = None

        if not home_loaded or not page:
            await asyncio.sleep(2)
            continue

        try:
            # Aguarda disparo inicial do gtag.js e pixel.wp.com na Home
            await asyncio.sleep(random.uniform(4.0, 6.0))

            num_artigos = random.randint(ARTIGOS_POR_CICLO_MIN, ARTIGOS_POR_CICLO_MAX)
            print(f"[BOT {bot_id}] Home carregada! Lendo {num_artigos} notícias...")

            for i in range(num_artigos):
                await slow_scroll(page, random.randint(250, 450), 2)
                await asyncio.sleep(1.0)

                article_urls = await get_article_links(page)

                if article_urls:
                    url_alvo = random.choice(article_urls[:18])
                    try:
                        print(f"[BOT {bot_id}] [Notícia {i+1}/{num_artigos}] Lendo: {url_alvo}")
                        await page.goto(
                            url_alvo,
                            wait_until="domcontentloaded",
                            referer="https://plantaocnp.com/",
                            timeout=TIMEOUT_PAGINA
                        )
                        await asyncio.sleep(random.uniform(2.5, 4.0))

                        read_time = random.randint(TEMPO_LEITURA_MIN, TEMPO_LEITURA_MAX)
                        speed_mult = random.uniform(0.7, 1.3)
                        dist_mult = random.uniform(0.7, 1.4)

                        await simulate_human_engagement(page, read_time, speed_mult, dist_mult)
                        await flush_analytics_events(page)
                    except Exception:
                        # Se uma matéria demorar no proxy, passa para a próxima sem derrubar o ciclo
                        pass
                else:
                    try:
                        await page.goto("https://plantaocnp.com/", wait_until="domcontentloaded", timeout=TIMEOUT_CONEXAO_PROXY)
                        await asyncio.sleep(3)
                    except Exception:
                        break
                    continue

                # Volta para a Home
                try:
                    await page.evaluate("window.scrollTo({top: 0, behavior: 'auto'});")
                    logo_element = await get_home_logo_locator(page)
                    if logo_element:
                        await logo_element.click(timeout=10000)
                    else:
                        await page.locator("a:has-text('Home'), a:has-text('Início')").first.click(timeout=10000)
                except Exception:
                    try:
                        await page.goto("https://plantaocnp.com/", wait_until="domcontentloaded", timeout=TIMEOUT_CONEXAO_PROXY)
                    except Exception:
                        pass

                await asyncio.sleep(random.uniform(2.5, 4.5))

            await flush_analytics_events(page)

            # Se o proxy funcionou e gerou hits no Analytics, promove para o Pool Ouro!
            if proxy_str and (ga_hits > 0 or wp_hits > 0):
                await proxy_manager.report_success(proxy_str)

            print(f"[BOT {bot_id}] [+] Ciclo finalizado com sucesso! (GA4: {ga_hits} hits | WP-Stats: {wp_hits} hits)")

        except Exception:
            if proxy_str:
                await proxy_manager.report_failure(proxy_str)
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

        tempo_espera = random.randint(ESPERA_SUCESSO_MIN, ESPERA_SUCESSO_MAX)
        await asyncio.sleep(tempo_espera)


async def background_proxy_refresher():
    """Mantém o pool de proxies sempre abastecido em segundo plano a cada 3 minutos."""
    while True:
        await asyncio.sleep(180)
        try:
            await proxy_manager.refresh_proxies()
        except Exception:
            pass


async def main():
    print("=" * 70)
    print(f"[+] INICIANDO {QTD_BOTS} BOTS SIMULTÂNEOS EM PLANTAOCNP.COM (ALTA ESCALA GA4)")
    print(f"[+] Arquitetura: {QTD_NAVEGADORES_BASE} Motores Chromium Compartilhados + Validação Direta no Site")
    print("=" * 70)

    await proxy_manager.refresh_proxies()

    async with async_playwright() as p:
        browser_pool = BrowserPool(p, size=QTD_NAVEGADORES_BASE)
        asyncio.create_task(background_proxy_refresher())

        tarefas = [run_bot(i + 1, browser_pool) for i in range(QTD_BOTS)]
        await asyncio.gather(*tarefas)


if __name__ == "__main__":
    auto_install_chromium()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Aplicação Encerrada pelo usuário.")
