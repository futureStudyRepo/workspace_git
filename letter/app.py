import os
import pymysql
import pandas as pd
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
# jinja2 pandas fastapi pymysql python-multipart uvicorn
# DB 설정 (EC2/도커 환경에서는 'localhost' 대신 호스트 IP나 서비스명을 사용해야 할 수 있습니다)
db_config ={
     'host':'mysql-container-name'
    ,'user':'myuser'
    ,'password':'myuser'
    ,'database':'mydb'
}

def get_connection():
    return pymysql.connect(**db_config)

app = FastAPI(title="Love Letter App (FastAPI)")

# EC2/Nginx 등 리버스 프록시 환경을 위한 미들웨어 추가
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- 메인 화면 (레터 조회) ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(name="index.html", request=request)
# --- 레터 작성 폼 화면 ---
@app.get("/form", response_class=HTMLResponse)
def letter_form(request: Request):
    return templates.TemplateResponse(name="letterForm.html", request=request)
# --- 레터 데이터 DB 저장 (INSERT) ---
@app.post("/sendLetter", response_class=HTMLResponse)
def send_letter(
    request: Request,
    toNm: str = Form(...),      # 절대 제출해! (필수 값)
    email: str = Form(...),
    messageOne: str = Form(" "), # 제출 안하면 빈칸으로 제출해!
    messageTwo: str = Form(" "),
    messageThree: str = Form(" ")
):
    if toNm and email:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            sql = '''
                INSERT INTO cards (email, nm, message1, message2, message3)
                VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (email, toNm, messageOne, messageTwo, messageThree))
            conn.commit()
            conn.close()
            return RedirectResponse(url="/", status_code=303)
        except Exception as e:
            error_msg = f"DB 저장 중 오류 발생: {str(e)}"
            return templates.TemplateResponse(name="letterForm.html", request=request, context={"error": error_msg})
        
    return templates.TemplateResponse(name="letterForm.html", request=request, context={"error": "이메일과 받는 분 이름이 필요합니다."})

# --- 레터 데이터 조회 ---
@app.post("/get_card", response_class=HTMLResponse)
def get_card(request: Request
           , toNm: str = Form(...)
           , email: str = Form(...)): 
    if toNm != '' and email !='':
        try:
            conn = get_connection()
            card = pd.read_sql(sql='''
                SELECT *
                FROM cards
                WHERE email = %s
                AND   nm = %s
            ''', con=conn, params=(email,toNm))
            conn.close()
            
            if not card.empty:
                return templates.TemplateResponse(name="letter_result.html", request=request, context={
                    "message1": card.iloc[0]['message1'],
                    "message2": card.iloc[0]['message2'],
                    "message3": card.iloc[0]['message3'],
                    "nm": toNm,
                    "email": email
                })
            else:
                return templates.TemplateResponse(name="index.html", request=request, context={"error": "등록된 러브레터가 없습니다 ㅠㅠ"})
        except Exception as e:
            error_msg = f"DB 조회 중 오류 발생: {str(e)}"
            return templates.TemplateResponse(name="index.html", request=request, context={"error": error_msg})
    else:
        return templates.TemplateResponse(name="index.html",request=request, context={"error": "이름과 이메일을 정확히 입력하세요."})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
