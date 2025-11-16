// probe-action/probe.js
const puppeteer = require("puppeteer");

// 👉 Mets ici toutes tes apps Streamlit à réveiller
const TARGET_URLS = [
  "https://f1-fastanalytics.streamlit.app/",
  "https://watchanalytics.streamlit.app/",
];

const PAGE_LOAD_TIMEOUT_MS = 20000;

// On va tester plusieurs formulations possibles du bouton de réveil
const WAKE_UP_KEYWORDS = [
  "wake up",
  "get this app back up",
  "réveiller cette application",
];

async function wakeUrl(url) {
  console.log(`\n=== Probe sur ${url} ===`);
  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    console.log(`Navigation vers ${url} ...`);
    await page.goto(url, { waitUntil: "networkidle2", timeout: PAGE_LOAD_TIMEOUT_MS });

    console.log("Page chargée, recherche d'un bouton de réveil éventuel...");

    // On récupère tous les éléments cliquables potentiels
    const candidates = await page.$$("button, a, div, span");

    let clicked = false;
    for (const el of candidates) {
      const text = (await page.evaluate((node) => node.innerText || "", el)).trim().toLowerCase();

      if (!text) continue;

      // On regarde si le texte contient une des expressions attendues
      if (WAKE_UP_KEYWORDS.some((kw) => text.includes(kw))) {
        console.log(`Bouton potentiel trouvé avec le texte : "${text}"`);
        await el.click();
        console.log("👉 Clic sur le bouton de réveil !");
        clicked = true;
        await page.waitForTimeout(5000); // on laisse le temps à l'app de se lancer
        break;
      }
    }

    if (!clicked) {
      console.log("Aucun bouton de réveil détecté, l'app est probablement déjà active ✅");
    } else {
      console.log("Réveil terminé (si tout s'est bien passé) ✅");
    }
  } catch (err) {
    console.error("Erreur pendant la probe :", err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

(async () => {
  for (const url of TARGET_URLS) {
    await wakeUrl(url);
  }
})();