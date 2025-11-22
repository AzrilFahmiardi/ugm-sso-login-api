from fastapi import FastAPI, HTTPException, Form
from playwright.sync_api import sync_playwright, TimeoutError
import re
import sys

app = FastAPI()

# URL Login Awal
SSO_URL = "https://sso.ugm.ac.id/cas/login?service=https%3A%2F%2Felok.ugm.ac.id%2Flogin%2Findex.php%3FauthCAS%3DCAS"

def perform_elok_login(username: str, password: str):
    """Fungsi login inti, diadaptasi dari script pengujian Anda."""
    
    
    with sync_playwright() as p:
        # mode headless
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(SSO_URL, wait_until="networkidle", timeout=30000)
            
            # 1. Mengisi Formulir Login
            page.fill("#username", username)
            page.fill("#password", password)
            
            # 2. Klik tombol Login dan Tunggu Navigasi
            page.click('input[name="submit"]')
            
            # Tunggu hingga diarahkan ke halaman ELOK (yang sukses login)
            page.wait_for_url("https://elok.ugm.ac.id/**", timeout=30000)

            # 3. Ekstraksi Sesskey
            html_content = page.content()
            sesskey_match = re.search(r'"sesskey":"(.+?)"', html_content)
            sesskey = sesskey_match.group(1) if sesskey_match else None

            # 4. Ekstraksi MoodleSession Cookie
            cookies = context.cookies()
            moodle_cookie = None
            
            for cookie in cookies:
                if cookie['name'] == 'MoodleSession':
                    moodle_cookie = f"{cookie['name']}={cookie['value']}"
                    break
            
            browser.close()
            
            if not sesskey or not moodle_cookie:
                raise ValueError("Gagal mengekstrak kunci sesi Moodle (sesskey atau MoodleSession).")
            
            return {
                "status": "success",
                "sesskey": sesskey,
                "moodle_cookie": moodle_cookie
            }

        except TimeoutError:
            browser.close()
            raise HTTPException(status_code=408, detail="Login Gagal: Timeout saat menyelesaikan rantai SSO.")
        except Exception as e:
            browser.close()
            # Ini akan menangkap error seperti kegagalan kredensial
            raise HTTPException(status_code=401, detail=f"Login Gagal: Kredensial Tidak Valid atau Error Internal. {e}")


# --- Endpoint API untuk n8n ---
@app.post("/login")
def login_endpoint(username: str = Form(...), password: str = Form(...)):
    """Menerima kredensial dari n8n dan mengembalikan sesi ELOK."""
    try:
        return perform_elok_login(username, password)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

if __name__ == "__main__":
    # Jalankan server untuk pengujian lokal
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)