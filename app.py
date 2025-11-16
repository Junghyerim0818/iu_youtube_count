from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
import json
import os     
import time
import threading

app = Flask(__name__)

# 마지막 업데이트 시간 파일 경로
LAST_UPDATE_TIME_FILE = 'last_update_time.json'

def load_last_update_time():
    """파일에서 마지막 업데이트 시간 로드"""
    global last_update_time
    if os.path.exists(LAST_UPDATE_TIME_FILE):
        try:
            with open(LAST_UPDATE_TIME_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                time_str = data.get('last_update_time')
                if time_str:
                    seoul_tz = ZoneInfo('Asia/Seoul')
                    try:
                        if 'T' in time_str:
                            if '+' in time_str or time_str.endswith('Z'):
                                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                if dt.tzinfo:
                                    dt = dt.astimezone(seoul_tz)
                                else:
                                    dt = dt.replace(tzinfo=seoul_tz)
                            else:
                                dt = datetime.fromisoformat(time_str).replace(tzinfo=seoul_tz)
                        else:
                            dt = datetime.fromisoformat(time_str + 'T00:00:00').replace(tzinfo=seoul_tz)
                        
                        last_update_time = dt
                        print(f"마지막 업데이트 시간 로드: {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        return last_update_time
                    except ValueError as e:
                        print(f"시간 파싱 오류: {e}")
        except Exception as e:
            print(f"마지막 업데이트 시간 로드 실패: {e}")
    return None

def save_last_update_time():
    """파일에 마지막 업데이트 시간 저장"""
    global last_update_time
    if last_update_time:
        try:
            with open(LAST_UPDATE_TIME_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_update_time': last_update_time.isoformat()
                }, f, ensure_ascii=False, indent=2)
            print(f"마지막 업데이트 시간 저장: {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"마지막 업데이트 시간 저장 실패: {e}")

# 서버 시작 시 마지막 업데이트 시간 로드
last_update_time = load_last_update_time()

# 캐시된 비디오 데이터
cached_mv_videos = None
cached_live_videos = None

# 이전 조회수 저장 (비디오 ID를 키로 사용)
previous_view_counts = {}

# 뮤직비디오 ID 리스트
MV_LIST = ['Ct8NZdYWOFI','g3TP6XZ1Baw','0ZukHxqOA0o','slT80EySpKk','BYQBs_4-MOo','7WINyXmPRAE','GHu39FEFIks','cxcxskPKtiI','Rh5ok0ljrzA','f_iQRO5BdCM','ouR4nn1G9r4','qGWZUtfV3IU','BkLKEsh6tZU','EiVmQZwJhsA','jeqdYqsrsA0','npttud7NkL0','js3PTlQFakk','BzYnNdJhZQw','86BST8NIpNM','d9IxdwEFk1c','R3Fwdnij49o','TgOu00Mf3kI','NJR8Inf77Ac','42Gtm4-Ax2U','v7bnOxV4jAc','nM0xDI5R50E','sqgxcCjD04s','D1PvIWdJ8xo','0-q1KafFCLU','Hsuy_xzPyWQ','VIDQTyNmkN4','c9E2IT1jHQY','l5Z1PBJLUss','ZXmoJu81e6A','6J9ixwhDYSM','mFbILexYSQg','JleoAppaxi0','kHW-UVXOcLU']

# 라이브클립 ID 리스트
LIVE_LIST = ['JtFI8dtPvxI','8zsYZFvKniw','m7mvpe1fVa4','L1JUfCyeT5E','3mk-DIcvVGU','3nDzKulmSpg','r3WS1BOpgk4','j3Aa1dgg8UI','FAI2wj2JGCI','UCQHgJ4uRwo','SmQhRHS9-YA','mcnFWBLrdCs','Xco5vbBmF5c','sAbU4fAqjZk','O-1FpjPP6_c','-_14Lhw0y1A','9WKzt9QEmD4','pDvBiB1waBk','nn1pbxe8bAI','o_nxIQTM_B0','3iM_06QeZi8','tJM0yIbg8iQ','OcVmaIlHZ1o','ax1csKKQnns','Cxzzg7L3Xgc']

def get_next_update_time():
    """다음 10분 단위 업데이트 시간 계산 (서울표준시 기준, 00분 기준)"""
    # 서울 시간대 가져오기
    seoul_tz = ZoneInfo('Asia/Seoul')
    now_seoul = datetime.now(seoul_tz)
    
    # 현재 분의 10분 단위 나머지
    minute_remainder = now_seoul.minute % 10
    # 나머지가 0이면 다음 10분 단위(10분 추가), 아니면 다음 10분 단위로 올림
    if minute_remainder == 0:
        minutes_to_add = 10
    else:
        minutes_to_add = 10 - minute_remainder
    # 초와 마이크로초를 0으로 설정하고 분 추가
    next_update = now_seoul.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    
    return next_update

def get_prev_update_time(dt=None):
    """이전(바닥) 10분 단위 시간 계산 (서울표준시 기준)"""
    seoul_tz = ZoneInfo('Asia/Seoul')
    if dt is None:
        dt = datetime.now(seoul_tz)
    else:
        if dt.tzinfo:
            dt = dt.astimezone(seoul_tz)
        else:
            dt = dt.replace(tzinfo=seoul_tz)
    floored_minute = (dt.minute // 10) * 10
    return dt.replace(minute=floored_minute, second=0, microsecond=0)

def fetch_batch_videos(video_ids_batch, previous_view_counts_dict=None):
    """배치로 비디오 정보 가져오기 (최대 50개)"""
    API_KEY = 'AIzaSyAmmehmaqCrWbKFwO6HhWMvQNtbbMDDaPQ'
    videos = []
    
    if not video_ids_batch:
        return videos
    
    if previous_view_counts_dict is None:
        previous_view_counts_dict = {}
    
    try:
        # 여러 비디오 ID를 콤마로 구분하여 한 번에 요청
        video_ids_str = ','.join(video_ids_batch)
        url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={video_ids_str}&key={API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # 응답에 오류가 있는지 확인
        if 'error' in data:
            print(f"API 오류: {data['error']}")
            return videos
        
        # items 처리
        if 'items' in data:
            # 응답 데이터를 video_id로 매핑
            video_data_map = {item['id']: item for item in data['items']}
            
            # 원래 순서대로 처리
            for video_id in video_ids_batch:
                if video_id in video_data_map:
                    item = video_data_map[video_id]
                    view_count = item.get('statistics', {}).get('viewCount', '0')
                    video_name = item.get('snippet', {}).get('title', '제목 없음')
                    published_at = item.get('snippet', {}).get('publishedAt', '')
                    thumbnails = item.get('snippet', {}).get('thumbnails', {})
                    
                    # 고화질 썸네일 우선순위: maxres > high > medium > default
                    thumbnail_url = (thumbnails.get('maxres', {}).get('url') or
                                   thumbnails.get('high', {}).get('url') or
                                   thumbnails.get('medium', {}).get('url') or
                                   thumbnails.get('default', {}).get('url', ''))
                    
                    view_count_int = int(view_count)
                    
                    # 이전 조회수 가져오기
                    previous_view_count = previous_view_counts_dict.get(video_id, view_count_int)
                    view_count_change = view_count_int - previous_view_count
                    
                    videos.append({
                        'title': video_name,
                        'view_count': format(view_count_int, ','),
                        'view_count_raw': view_count_int,
                        'published_at': published_at,
                        'published_at_raw': published_at,  # 정렬용
                        'thumbnail': thumbnail_url,
                        'video_id': video_id,
                        'view_count_change': view_count_change,
                        'view_count_change_formatted': format(view_count_change, ',') if view_count_change != 0 else '0'
                    })
                else:
                    print(f"비디오 ID {video_id}에 대한 데이터를 찾을 수 없습니다.")
                    
    except requests.exceptions.RequestException as e:
        print(f"네트워크 오류: {e}")
    except (KeyError, ValueError, IndexError) as e:
        print(f"데이터 파싱 오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
    
    return videos

def get_view_count(video_list, update_timestamp=True):
    """비디오 조회수 가져오기 (배치 요청 + 병렬 처리) - 정렬은 클라이언트에서 수행"""
    global last_update_time, previous_view_counts
    
    if not video_list:
        return []
    
    videos = []
    
    # 비디오 리스트를 50개씩 배치로 나누기 (YouTube API 제한)
    batch_size = 50
    batches = [video_list[i:i + batch_size] for i in range(0, len(video_list), batch_size)]
    
    # 병렬 처리로 여러 배치를 동시에 요청
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_batch = {executor.submit(fetch_batch_videos, batch, previous_view_counts): batch for batch in batches}
        
        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_videos = future.result()
                videos.extend(batch_videos)
            except Exception as e:
                print(f"배치 처리 오류: {e}")
    
    # 기본 정렬: 조회수 내림차순 (클라이언트에서 재정렬 가능)
    videos.sort(key=lambda x: x.get('view_count_raw', 0), reverse=True)
    
    # 현재 조회수를 이전 조회수로 저장 (다음 업데이트를 위해)
    if update_timestamp:
        for video in videos:
            previous_view_counts[video['video_id']] = video['view_count_raw']
        # 최종 업데이트 시간을 10분 단위 경계로 설정
        last_update_time = get_prev_update_time()
        save_last_update_time()
    
    return videos

@app.route('/')
def main():
    global last_update_time, cached_mv_videos, cached_live_videos
    
    # 캐시된 데이터가 없으면 초기 데이터만 가져오기 (시간 업데이트 안 함)
    if cached_mv_videos is None or cached_live_videos is None:
        # 초기 데이터 가져오기 (시간은 업데이트하지 않음)
        cached_mv_videos = get_view_count(MV_LIST, update_timestamp=False)
        cached_live_videos = get_view_count(LIVE_LIST, update_timestamp=False)
        
        # last_update_time이 None이면 초기 시간 설정 (한 번만, 서버 시작 시)
                # last_update_time이 여전히 None이면 (파일에서도 로드 못한 경우)
        if last_update_time is None:
            # 파일에서 다시 로드 시도
            last_update_time = load_last_update_time()
            # 파일에서도 로드 못한 경우에만 현재 시간 사용 (파일에는 저장하지 않음)
            if last_update_time is None:
                # 최초 진입 시에도 10분 단위 경계 시간으로 설정
                last_update_time = get_prev_update_time()
                print(f"초기 업데이트 시간 설정 (첫 실행, 파일 미저장): {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")
                # 첫 실행이므로 파일에 저장하지 않음 (실제 업데이트 시에만 저장)
    
    # 마지막 업데이트 시간 포맷팅 (항상 설정된 시간 사용)
    if last_update_time:
        update_time = last_update_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # fallback: 현재 시간을 10분 단위로 내림
        update_time = get_prev_update_time().strftime('%Y-%m-%d %H:%M:%S')
    
    next_update_time = get_next_update_time()
    seoul_tz = ZoneInfo('Asia/Seoul')
    server_time = datetime.now(seoul_tz)
    return render_template('main.html', 
                         mv_videos=cached_mv_videos or [],
                         live_videos=cached_live_videos or [],
                         update_time=update_time,
                         next_update_time=next_update_time.isoformat(),
                         server_time=server_time.isoformat())

@app.route('/api/update')
def update_data():
    global last_update_time, cached_mv_videos, cached_live_videos
    
    # 백그라운드 스케줄러가 주기적으로 갱신하므로 여기서는 캐시만 반환
    if cached_mv_videos is None or cached_live_videos is None:
        # 캐시가 아직 없으면 초기 로드만 수행 (시간 업데이트 안 함)
        cached_mv_videos = get_view_count(MV_LIST, update_timestamp=False)
        cached_live_videos = get_view_count(LIVE_LIST, update_timestamp=False)
    
    # 마지막 업데이트 시간 포맷팅
    if last_update_time:
        update_time = last_update_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        update_time = get_prev_update_time().strftime('%Y-%m-%d %H:%M:%S')
    
    next_update_time = get_next_update_time()
    seoul_tz = ZoneInfo('Asia/Seoul')
    server_time = datetime.now(seoul_tz)
    return jsonify({
        'mv_videos': cached_mv_videos,
        'live_videos': cached_live_videos,
        'update_time': update_time,
        'next_update_time': next_update_time.isoformat(),
        'server_time': server_time.isoformat()
    })

def _background_updater():
    """10분 단위 경계에 맞춰 주기적으로 데이터 갱신"""
    global cached_mv_videos, cached_live_videos
    while True:
        try:
            # 다음 경계 시각까지 대기
            next_time = get_next_update_time()
            now = datetime.now(ZoneInfo('Asia/Seoul'))
            sleep_seconds = max(0.0, (next_time - now).total_seconds()) + 1.0
            time.sleep(sleep_seconds)
            # 데이터 갱신 (시간은 내부에서 10분 경계로 기록)
            cached_mv_videos = get_view_count(MV_LIST, update_timestamp=True)
            cached_live_videos = get_view_count(LIVE_LIST, update_timestamp=True)
            print(f"백그라운드 갱신 완료: {get_prev_update_time().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"백그라운드 갱신 오류: {e}")
            # 오류 시 잠깐 대기 후 재시도
            time.sleep(5)

def _start_background_thread():
    """Flask 디버그 리로더 중복 실행 방지하여 스레드 시작"""
    should_start = True
    if app.debug:
        # werkzeug 리로더 환경에서 메인 프로세스만 실행
        should_start = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if should_start:
        t = threading.Thread(target=_background_updater, daemon=True)
        t.start()

if __name__ == '__main__':
    _start_background_thread()
    app.run(port = 80, host='0.0.0.0', debug=True)

