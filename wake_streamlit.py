import time
import requests

APP_URLS = [
    "https://f1-fastanalytics.streamlit.app/",
    "https://watchanalytics.streamlit.app/"
]

TIMEOUT = 30  # secondes


def wake_app(url: str) -> None:
    print(f"Réveil de {url} ...")
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        print(f"Status code: {resp.status_code}")

        # Petit log pour comprendre si on tombe sur une page d’hibernation
        text_sample = resp.text[:500].lower()
        if "this app has gone to sleep" in text_sample or "wake up" in text_sample:
            print("⚠️ On dirait la page de veille / wake-up.")
        else:
            print("✅ La page semble répondre normalement.")
    except Exception as e:
        print(f"❌ Erreur pour {url}: {e}")


def main():
    for url in APP_URLS:
        wake_app(url)
        time.sleep(5)


if __name__ == "__main__":
    main()