const puppeteer = require('puppeteer');

// 👉 Liste des apps à réveiller
const TARGET_URLS = [
  "https://f1-fastanalytics.streamlit.app/",
  "https://watchanalytics.streamlit.app/",
];

const WAKE_UP_BUTTON_TEXT = "app back up";
const PAGE_LOAD_GRACE_PERIOD_MS = 8000;

console.log(process.version);

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    ignoreHTTPSErrors: true,
    args: ['--no-sandbox'],
  });

  // Fonction de check pour une page ou un frame
  const checkForHibernation = async (target, url) => {
    // On cherche un bouton qui contient le texte du bouton de réveil
    const [button] = await target.$x(`//button[contains(., '${WAKE_UP_BUTTON_TEXT}')]`);
    if (button) {
      console.log(`App hibernating pour ${url}. Attempting to wake up!`);
      await button.click();
    } else {
      console.log(`Aucun bouton de réveil détecté pour ${url} (probablement déjà active).`);
    }
  };

  try {
    for (const url of TARGET_URLS) {
      console.log(`\n=== Probe sur ${url} ===`);
      const page = await browser.newPage();

      console.log("Ouverture de la page...");
      await page.goto(url, { waitUntil: 'networkidle2' }).catch(async (e) => {
        console.log(`Erreur de navigation vers ${url}:`, e.message || e);
      });

      // Attente que la page de veille ou l'app se charge
      await page.waitForTimeout(PAGE_LOAD_GRACE_PERIOD_MS);

      // 1️⃣ On vérifie sur la page principale
      await checkForHibernation(page, url);

      // 2️⃣ On vérifie aussi dans les frames (au cas où Streamlit encapsule le contenu)
      const frames = page.frames();
      for (const frame of frames) {
        await checkForHibernation(frame, url);
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