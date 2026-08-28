import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("KEENTOOLS_API_KEY")

if not API_KEY:
    raise ValueError("API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")

BASE_URL = "https://api.cloud.keentools.io/v1/avatar"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def create_3d_avatar(image_folder="input_images", output_file="keentools_head.zip"):
    img_dir = Path(image_folder)
    
    if not img_dir.exists():
        raise FileNotFoundError(f"'{image_folder}' 폴더가 없습니다. 폴더를 생성하고 사진을 넣어주세요.")
        
    valid_extensions = {".jpg", ".jpeg", ".png"}
    image_paths = [p for p in img_dir.iterdir() if p.suffix.lower() in valid_extensions]
    
    if not image_paths:
        print(f"[-] '{image_folder}' 폴더에 유효한 이미지 파일이 없습니다.")
        return
    
    if len(image_paths) > 15:
         print("[!] 이미지가 너무 많습니다. 처리 효율을 위해 15장으로 제한합니다.")
         image_paths = image_paths[:15]

    print(f"[+] 총 {len(image_paths)}장의 사진을 찾았습니다. 처리를 시작합니다.")
    
    print("\n[*] [1/5] KeenTools API 세션 초기화 중...")
    init_res = requests.post(
        f"{BASE_URL}/init", 
        headers=HEADERS, 
        json={"image_count": len(image_paths)}
    )
    init_res.raise_for_status()
    init_data = init_res.json()
    
    avatar_id = init_data["avatar_id"]
    upload_urls = init_data["upload_urls"]
    print(f"[+] Avatar ID 발급 완료: {avatar_id}")

    print("\n[*] [2/5] 이미지 파일 업로드 중...")
    for path, upload_url in zip(image_paths, upload_urls):
        content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        
        with open(path, "rb") as f:
            upload_res = requests.put(
                upload_url,
                headers={"Content-Type": content_type},
                data=f.read()
            )
            upload_res.raise_for_status()
        print(f"    - 업로드 완료: {path.name}")

    print("\n[*] [3/5] 3D 모델 재구성 요청 중...")
    process_res = requests.post(
        f"{BASE_URL}/{avatar_id}/process",
        headers=HEADERS,
        json={
            "focal_length_type": {"focal_length_type": "estimate_common"} 
        }
    )
    process_res.raise_for_status()

    print("\n[*] [4/5] 클라우드 3D 렌더링 진행 중 (수 분 정도 소요될 수 있습니다)...")
    while True:
        status_res = requests.get(f"{BASE_URL}/{avatar_id}/get-status", headers=HEADERS)
        status_res.raise_for_status()
        status_data = status_res.json()
        
        status = status_data.get("status")
        if status == "completed":
            print("[+] 3D 재구성 렌더링 완료!")
            break
        elif status == "failed":
            raise RuntimeError(f"[-] 3D 재구성 실패: {status_data}")
        
        print(f"    ... 진행 상태: {status}")
        time.sleep(5)  

    print("\n[*] [5/5] 결과물 3D 모델 다운로드 중...")
    model_url = f"{BASE_URL}/{avatar_id}/get-3d-model?mesh_format=obj&texture=jpg"
    dl_res = requests.get(model_url, headers=HEADERS, stream=True)
    dl_res.raise_for_status()
    
    with open(output_file, "wb") as f:
        for chunk in dl_res.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print(f"\n[+] 모든 과정이 완료되었습니다")
    print(f"[+] 결과 파일 저장 위치: {Path(output_file).absolute()}")

if __name__ == "__main__":
    try:
        create_3d_avatar(image_folder="input_images", output_file="keentools_head.zip")
    except Exception as e:
        print(f"\n[!] 오류가 발생했습니다: {e}")