const puppeteer = require('puppeteer');

// 👉 Liste des apps à réveiller
const TARGET_URLS = [
  "https://f1-fastanalytics.streamlit.app/",
  "https://watchanalytics.streamlit.app/",
];

// On cherche un morceau de texte suffisamment distinctif du bouton
// (on ne met pas tout le texte exact pour éviter les soucis de casse / espaces)
const WAKE_UP_BUTTON_SUBSTRING = "app back up";

const PAGE_LOAD_GRACE_PERIOD_MS = 8000;
const POST_CLICK_WAIT_MS = 20000; // temps d'attente après clic (20s)

console.log("Node version:", process.version);

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    ignoreHTTPSErrors: true,
    args: ['--no-sandbox'],
  });

  // Fonction qui tente de trouver et cliquer sur le bouton de réveil
  const tryWakeInTarget = async (target, url, contextLabel) => {
    // XPath plus robuste : on passe tout en lowercase côté DOM
    const wakeXpath =
      "//button[contains(" +
      "translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), " +
      `'${WAKE_UP_BUTTON_SUBSTRING.toLowerCase()}'` +
      ")]";

    const buttons = await target.$x(wakeXpath);

    if (!buttons || buttons.length === 0) {
      console.log(`[${contextLabel}] Aucun bouton de réveil détecté pour ${url}.`);
      return false;
    }

    console.log(
      `[${contextLabel}] Bouton de réveil détecté pour ${url} (count=${buttons.length}). Clic en cours...`
    );

    await buttons[0].click();

    // On laisse le temps à l'action de se déclencher
    await target.waitForTimeout(POST_CLICK_WAIT_MS);

    // On vérifie si le message de veille est toujours présent
    const html = (await target.content()).toLowerCase();
    if (html.includes("this app has gone to sleep") || html.includes("zzzz")) {
      console.log(
        `[${contextLabel}] ⚠️ Après le clic, la page semble montrer encore l'écran de veille pour ${url}.`
      );
    } else {
      console.log(
        `[${contextLabel}] ✅ Après le clic, la page ne montre plus l'écran de veille pour ${url} (ou le HTML a changé).`
      );
    }

    return true;
  };

  try {
    for (const url of TARGET_URLS) {
      console.log(`\n=== Probe sur ${url} ===`);
      const page = await browser.newPage();

      console.log("Ouverture de la page...");
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 }).catch(async (e) => {
        console.log(`Erreur de navigation vers ${url}:`, e.message || e);
      });

      // Attente initiale pour laisser charger la page (veille ou app)
      await page.waitForTimeout(PAGE_LOAD_GRACE_PERIOD_MS);

      // 1️⃣ On essaie d'abord sur la page principale
      let woke = await tryWakeInTarget(page, url, "main");

      // 2️⃣ Si on n'a rien trouvé/clické, on tente dans les frames
      if (!woke) {
        const frames = page.frames();
        for (const frame of frames) {
          woke = await tryWakeInTarget(frame, url, "frame");
          if (woke) break;
        }
      }

      await page.close();
      console.log(`Fin du traitement pour ${url}`);
    }
  } catch (err) {
    console.error("Erreur pendant la probe :", err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();