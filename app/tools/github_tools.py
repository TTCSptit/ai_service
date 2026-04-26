import os
import httpx 
import base64
import concurrent.futures
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from app.core.logger import logger
from app.core.config import settings
from app.core.llm import get_llm_cheap_v1, get_llm_cheap_v2

_GITHUB_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def is_garbage_file(path: str) -> bool:
    path = path.lower()
    garbage_dirs = ['node_modules/', 'venv/', 'build/', 'dist/', '.git/', 'vendor/', '__pycache__/']
    garbage_exts = ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp4', '.woff', '.ttf', '.eot',
                    '.lock', 'package-lock.json', 'yarn.lock', '.gitignore', '.csv', '.json', '.md',
                    '.css', '.scss', '.less', '.html', '.txt']

    if any(gd in path for gd in garbage_dirs):
        return True
    if any(path.endswith(ext) for ext in garbage_exts):
        return True
    return False


def score_file(path: str) -> int:
    path_lower = path.lower()
    score = 0
    core_names = ['main.py', 'app.py', 'index.js', 'server.js', 'app.tsx', 'index.tsx', 'app.jsx',
                  'main.jsx', 'app.js', 'main.go', 'application.java', 'views.py', 'models.py',
                  'controller', 'service']
    if any(name in path_lower for name in core_names):
        score += 100

    important_dirs = ['src/', 'app/', 'lib/', 'controllers/', 'services/', 'api/', 'components/']
    if any(d in path_lower for d in important_dirs):
        score += 50

    return score


@tool
def analyze_github_profile(username_or_url: str) -> str:
    """
    Công cụ thu thập mã nguồn thực tế từ Github. Sử dụng công cụ này BẤT CỨ KHI NÀO ứng viên cung cấp link mạng xã hội Github hoặc nhắc đến username Github của họ.
    Tham số:
    - username_or_url: Tên đăng nhập (username) hoặc đường dẫn trực tiếp (url) tới Github profile hoặc 1 Repo Github cụ thể.
    """
    input_str = username_or_url.strip().strip('/')
    username = ""
    specific_repo = ""

    if 'github.com/' in input_str:
        parts = input_str.split('github.com/')[-1].split('/')
        username = parts[0]
        if len(parts) >= 2 and parts[1]:
            specific_repo = parts[1]
    else:
        username = input_str

    logger.info(f"[Github Fetcher] Đang tải mã nguồn của User/Repo: {username}/{specific_repo if specific_repo else 'Tất cả'}...")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Career-Advisor"
    }

    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    try:
        repos = []
        # FIX Bug 2: Dùng httpx.Client (sync) thay requests.get — thread-safe, timeout rõ ràng
        with httpx.Client(headers=headers, timeout=_GITHUB_TIMEOUT) as client:
            if specific_repo:
                single_repo_url = f"https://api.github.com/repos/{username}/{specific_repo}"
                res = client.get(single_repo_url)
                if res.status_code == 200:
                    repos = [res.json()]
                else:
                    return f"[THẤT BẠI] Không tìm thấy hoặc không có quyền truy cập repo: {username}/{specific_repo}"
            else:
                repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3"
                response = client.get(repos_url)

                if response.status_code == 404:
                    return f"[THẤT BẠI] Không tìm thấy tài khoản Github: {username}"
                elif response.status_code == 403:
                    return "[THẤT BẠI] Giới hạn gọi API Github (Rate Limit). Cần kiểm tra GITHUB_TOKEN."
                elif response.status_code != 200:
                    return f"[THẤT BẠI] Truy xuất Github. Mã lỗi: {response.status_code}"

                repos = response.json()
                if not repos:
                    return f"[THÔNG BÁO] Tài khoản {username} hiện không có repository public nào."

        report = f"==== THÔNG TIN SƠ BỘ TỪ GITHUB CỦA: {username.upper()} ====\n\n"

        raw_code_corpus = ""
        repo_count = 0

        for repo in repos:
            repo_count += 1
            repo_name = repo.get("name")
            language = repo.get("language", "Unknown")
            description = repo.get("description", "Không có mô tả")
            default_branch = repo.get("default_branch", "main")

            report += f">>> PROJECT: {repo_name} | Ngôn ngữ chính: {language}\n"
            report += f"- Mô tả: {description}\n"

            # Lấy toàn bộ cây thư mục
            tree_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{default_branch}?recursive=1"

            MAX_CHARS_PER_REPO = 30000
            repo_chars = 0

            with httpx.Client(headers=headers, timeout=_GITHUB_TIMEOUT) as client:
                tree_res = client.get(tree_url)

            if tree_res.status_code == 200:
                tree_data = tree_res.json().get("tree", [])

                # Lọc rác và tính điểm
                valid_files = [item for item in tree_data if item["type"] == "blob" and not is_garbage_file(item["path"])]
                valid_files.sort(key=lambda x: score_file(x["path"]), reverse=True)

                if not valid_files:
                    raw_code_corpus += f"\n\n[REPO: {repo_name}]\n- Không tìm thấy mã nguồn cốt lõi.\n"
                    continue

                raw_code_corpus += f"\n\n[REPO: {repo_name}]\n"

                # FIX Bug 2: fetch_file dùng httpx.Client — proper timeout, exception handling
                def fetch_file(file_item):
                    file_path = file_item["path"]
                    file_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/{default_branch}/{file_path}"
                    try:
                        with httpx.Client(timeout=_GITHUB_TIMEOUT) as c:
                            f_res = c.get(file_url, headers=headers)
                        if f_res.status_code == 200:
                            content = f_res.text
                            if len(content) > 15000:
                                content = content[:15000] + "\n...[CẮT]..."
                            return f"\n- FILE `{file_path}`:\n```\n{content}\n```\n", len(content)
                    except httpx.TimeoutException:
                        logger.warning(f"[Github Fetcher] Timeout khi đọc file: {file_path}")
                    except Exception as e:
                        logger.warning(f"[Github Fetcher] Lỗi đọc file {file_path}: {e}")
                    return f"- Không đọc được: `{file_path}`\n", 0

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(fetch_file, f) for f in valid_files[:15]]
                    for future in concurrent.futures.as_completed(futures):
                        f_text, f_len = future.result()
                        if repo_chars > MAX_CHARS_PER_REPO:
                            continue
                        raw_code_corpus += f_text
                        repo_chars += f_len
            else:
                report += "- Lỗi: Không thể lấy cấu trúc.\n"
            report += "\n"

        logger.info(f"[Github Fetcher] Hoàn tất quét raw {repo_count} dự án. Độ dài mã nguồn: {len(raw_code_corpus)} chars.")

        if len(raw_code_corpus.strip()) < 50:
            return report + "\n- KHÔNG CÓ MÃ NGUỒN NÀO ĐỂ PHÂN TÍCH."

        # ==========================================
        # Đội đặc nhiệm LLM (Map-Reduce)
        # ==========================================
        logger.info("[Github Fetcher] Đang khởi động 2 LLM phụ để tóm tắt mã nguồn...")

        prompt_quality = f"""Bạn là Senior Developer khó tính. Hãy đọc luồng mã nguồn Github sau và vạch trần các ĐIỂM YẾU (Bad Smells, Hard-code, N+1 Query, thiếu Validate, logic rác...).
HÃY TRÍCH CỤ THỂ 1-2 ĐOẠN CODE KHÔNG TỐT ĐỂ CHỨNG MINH. Dưới 250 chữ.
Mã Nguồn: {raw_code_corpus}"""

        prompt_arch = f"""Bạn là System Architect giỏi. Đọc mã nguồn Github sau và TÓM TẮT NHANH CẤU TRÚC:
- Dùng công nghệ/Framework gì?
- Cấu trúc thư mục, Clean Code hay không?
- Đánh giá chung về quy mô bài toán. Dưới 200 chữ.
Mã Nguồn: {raw_code_corpus}"""

        def run_quality():
            llm = get_llm_cheap_v1()
            return llm.invoke(prompt_quality).content

        def run_arch():
            llm = get_llm_cheap_v2()
            return llm.invoke(prompt_arch).content

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_q = executor.submit(run_quality)
            future_a = executor.submit(run_arch)

            quality_report = future_q.result()
            arch_report = future_a.result()

        executive_summary = f"""{report}
==== BÁO CÁO CÔ ĐẶC DÀNH CHO TECH LEAD ====

[1. TỔNG QUAN KIẾN TRÚC]
{arch_report}

[2. ĐÁNH GIÁ CHẤT LƯỢNG MÃ NGUỒN (ĐIỂM TRỪ)]
{quality_report}

---> LỆNH DÀNH CHO BẠN (TECH LEAD CHÍNH): Hãy dựa vào Báo cáo cô đặc này để CHÊ và "ÉP GÓC" ứng viên, ĐẶT CÂU HỎI VỀ ĐOẠN CODE BỊ LỖI Ở PHẦN 2! BẮT Buộc!
"""
        logger.info("[Github Fetcher] Tóm tắt hoàn tất.")
        return executive_summary

    except Exception as e:
        logger.error(f"[Github Fetcher Lỗi]: {e}", exc_info=True)
        return f"[LỖI HỆ THỐNG] Lỗi ngoại lệ khi gọi API: {str(e)}"
