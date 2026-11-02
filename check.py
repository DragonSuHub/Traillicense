import os
import sys
import requests
from bs4 import BeautifulSoup

URL = "https://lic.kotsa.or.kr/safety/module/resTsa/formApplyTsaCbt2.do?menu_idx=24"
KEYWORD = "접수하기"  # 감시할 버튼 문구
DEBUG = os.environ.get("DEBUG") == "1"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def send_telegram(text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=15,
    )
    r.raise_for_status()


def is_open(html: str) -> bool:
    """'접수하기' 버튼이 존재하고 비활성화(disabled 등)가 아니면 True."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = [
        el for el in soup.find_all(["a", "button", "input"])
        if KEYWORD in (el.get_text(strip=True) or el.get("value", ""))
    ]

    if DEBUG:
        print(f"[DEBUG] '{KEYWORD}' 포함 요소 {len(candidates)}개")
        for el in candidates:
            print("[DEBUG]", str(el)[:300])

    for el in candidates:
        classes = " ".join(el.get("class", [])).lower()
        disabled = (
            el.has_attr("disabled")
            or el.get("aria-disabled") == "true"
            or "disabled" in classes
            or "off" in classes.split()
            or "end" in classes.split()
        )
        if not disabled:
            return True
    return False


def dump(resp) -> None:
    """페이지가 실제로 어떻게 내려오는지 로그에 출력 (디버그용)."""
    soup = BeautifulSoup(resp.text, "html.parser")
    print(f"[DEBUG] status={resp.status_code} url={resp.url}")
    print(f"[DEBUG] 길이={len(resp.text)} title={soup.title.get_text(strip=True) if soup.title else None}")
    print(f"[DEBUG] script 태그 {len(soup.find_all('script'))}개, iframe {len(soup.find_all('iframe'))}개")
    words = ("접수", "신청", "마감", "예약", "로그인", "접근", "차단", "오류")
    seen = set()
    for line in soup.get_text("\n", strip=True).splitlines():
        if any(w in line for w in words) and line not in seen:
            seen.add(line)
            print("[DEBUG] 텍스트:", line[:120])
            if len(seen) >= 40:
                break
    print("[DEBUG] 본문 앞부분:", soup.get_text(" ", strip=True)[:300])


def main() -> None:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        # 접속 실패는 알림 없이 로그만 남김 (다음 실행에서 재시도)
        print(f"요청 실패: {e}")
        sys.exit(0)

    resp.encoding = resp.apparent_encoding
    if DEBUG:
        dump(resp)
    if is_open(resp.text):
        send_telegram(f"🚨 철도교통안전관리자 접수 버튼 활성화!\n지금 확인하세요 👉 {URL}")
        print("열림 감지 → 텔레그램 전송")
    else:
        print("아직 마감")


if __name__ == "__main__":
    main()
