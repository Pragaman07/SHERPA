from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def login_whatsapp():
    print("Initializing Selenium for WhatsApp Login...")
    options = webdriver.ChromeOptions()
    options.add_argument("user-data-dir=selenium_data") # Keep session
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")
        print("WhatsApp Web opened.")
        print("Please scan the QR code if you are not logged in.")
        print("The browser will remain open for 300 seconds (5 minutes) to allow you to log in.")
        time.sleep(300)
        print("Closing browser. Session should be saved.")
        driver.quit()
    except Exception as e:
        print(f"Failed to initialize Selenium: {e}")

if __name__ == "__main__":
    login_whatsapp()
