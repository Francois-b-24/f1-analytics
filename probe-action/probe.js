const puppeteer = require('puppeteer');

// 👉 Liste des apps à réveiller
const TARGET_URLS = [
  "https://f1-fastanalytics.streamlit.app/",
  "https://watchanalytics.streamlit.app/",
  "https://assettracket.streamlit.app/",
  "https://insuranalytics.streamlit.app/",
  "https://tennisanalytics.streamlit.app/",
];

// Fragment de texte du bouton de réveil Streamlit ("Yes, get this app back up!").
// On ne matche qu'une sous-chaîne pour rester tolérant à la casse et aux espaces.
const WAKE_UP_BUTTON_SUBSTRING = "app back up";

// Marqueurs de l'écran de veille, utilisés pour vérifier l'état après clic.
const SLEEP_MARKERS = ["this app has gone to sleep", "zzzz"];

const PAGE_LOAD_GRACE_PERIOD_MS = 8000;
const POST_CLICK_WAIT_MS = 20000;
const NAV_TIMEOUT_MS = 30000;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Cherche le bouton de réveil et clique dessus. Retourne true si un clic a eu lieu. */
const tryWakeInTarget = async (target, url, contextLabel) => {
  // `$x` a été retiré de Puppeteer : on filtre les boutons côté DOM via evaluate.
  let handles = [];
  try {
    handles = await target.$$('button');
  } catch (err) {
    console.log(`[${contextLabel}] Impossible de lister les boutons pour ${url}: ${err.message}`);
    return false;
  }

  for (const handle of handles) {
    let text = '';
    try {
      text = await handle.evaluate((el) => (el.textContent || '').trim().toLowerCase());
    } catch {
      continue; // handle détaché entre-temps
    }
    if (!text.includes(WAKE_UP_BUTTON_SUBSTRING)) continue;

    console.log(`[${contextLabel}] Bouton de réveil détecté pour ${url}. Clic en cours...`);
    try {
      await handle.click();
    } catch (err) {
      console.log(`[${contextLabel}] Clic échoué pour ${url}: ${err.message}`);
      return false;
    }

    await sleep(POST_CLICK_WAIT_MS);
    return true;
  }

  console.log(`[${contextLabel}] Aucun bouton de réveil détecté pour ${url}.`);
  return false;
};

/** Indique si la page affiche encore l'écran de veille. */
const isAsleep = async (page) => {
  try {
    const html = (await page.content()).toLowerCase();
    return SLEEP_MARKERS.some((marker) => html.includes(marker));
  } catch {
    return false;
  }
};

(async () => {
  console.log("Node version:", process.version);

  const browser = await puppeteer.launch({
    headless: true,
    acceptInsecureCerts: true,
    // En conteneur CI, le bac à sable et le gestionnaire de plantage de Chrome
    // n'ont pas les permissions nécessaires : crashpad fait échouer le
    // lancement ("--database is required"). On les désactive explicitement.
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-crash-reporter',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  });

  const failures = [];

  try {
    for (const url of TARGET_URLS) {
      console.log(`\n=== Probe sur ${url} ===`);
      const page = await browser.newPage();

      try {
        await page.goto(url, { waitUntil: 'networkidle2', timeout: NAV_TIMEOUT_MS });
      } catch (err) {
        // Une boucle de redirection (app -> /-/login -> app) se manifeste ici,
        // typiquement en ERR_TOO_MANY_REDIRECTS : c'est un incident plateforme,
        // pas une mise en veille — on le signale distinctement.
        const msg = err.message || String(err);
        if (/redirect/i.test(msg)) {
          console.log(`❌ ${url} : boucle de redirection (incident plateforme, pas une veille).`);
          failures.push(`${url} (boucle de redirection)`);
        } else {
          console.log(`❌ Erreur de navigation vers ${url}: ${msg}`);
          failures.push(`${url} (navigation: ${msg})`);
        }
        await page.close();
        continue;
      }

      // Redirigé vers l'écran de login : l'app n'est pas publiquement accessible.
      if (page.url().includes('/-/login')) {
        console.log(`❌ ${url} : redirigée vers /-/login — app inaccessible publiquement.`);
        failures.push(`${url} (redirection /-/login)`);
        await page.close();
        continue;
      }

      await sleep(PAGE_LOAD_GRACE_PERIOD_MS);

      // L'app dort-elle vraiment ? Si non, rien à faire.
      if (!(await isAsleep(page))) {
        console.log(`✅ ${url} est déjà éveillée.`);
        await page.close();
        continue;
      }

      console.log(`💤 ${url} est en veille — tentative de réveil.`);

      // 1) page principale, puis 2) frames éventuelles
      let clicked = await tryWakeInTarget(page, url, "main");
      if (!clicked) {
        for (const frame of page.frames()) {
          clicked = await tryWakeInTarget(frame, url, "frame");
          if (clicked) break;
        }
      }

      if (!clicked) {
        console.log(`❌ ${url} : en veille mais aucun bouton de réveil trouvé.`);
        failures.push(`${url} (bouton introuvable)`);
      } else if (await isAsleep(page)) {
        console.log(`❌ ${url} : toujours en veille après le clic.`);
        failures.push(`${url} (réveil sans effet)`);
      } else {
        console.log(`✅ ${url} réveillée avec succès.`);
      }

      await page.close();
    }
  } catch (err) {
    console.error("Erreur inattendue pendant la probe :", err);
    failures.push(`erreur globale: ${err.message}`);
  } finally {
    await browser.close();
  }

  console.log("\n=== Résumé ===");
  if (failures.length === 0) {
    console.log(`✅ ${TARGET_URLS.length}/${TARGET_URLS.length} app(s) OK.`);
  } else {
    // Sortie non nulle : le workflow doit échouer visiblement plutôt qu'en silence.
    console.error(`❌ ${failures.length}/${TARGET_URLS.length} app(s) en échec :`);
    failures.forEach((f) => console.error(`  - ${f}`));
    process.exitCode = 1;
  }
})();
