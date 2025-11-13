from flask import Flask, render_template, jsonify
import requests
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# 뮤직비디오 ID 리스트
MV_LIST = ['Ct8NZdYWOFI','g3TP6XZ1Baw','0ZukHxqOA0o','slT80EySpKk','BYQBs_4-MOo','7WINyXmPRAE','GHu39FEFIks','cxcxskPKtiI','Rh5ok0ljrzA','f_iQRO5BdCM','ouR4nn1G9r4','qGWZUtfV3IU','BkLKEsh6tZU','EiVmQZwJhsA','jeqdYqsrsA0','npttud7NkL0','js3PTlQFakk','BzYnNdJhZQw','86BST8NIpNM','d9IxdwEFk1c','R3Fwdnij49o','TgOu00Mf3kI','NJR8Inf77Ac','42Gtm4-Ax2U','v7bnOxV4jAc','nM0xDI5R50E','sqgxcCjD04s','D1PvIWdJ8xo','0-q1KafFCLU','Hsuy_xzPyWQ','VIDQTyNmkN4','c9E2IT1jHQY','l5Z1PBJLUss','ZXmoJu81e6A','6J9ixwhDYSM','mFbILexYSQg','JleoAppaxi0','kHW-UVXOcLU']

# 라이브클립 ID 리스트
LIVE_LIST = ['JtFI8dtPvxI','8zsYZFvKniw','m7mvpe1fVa4','L1JUfCyeT5E','3mk-DIcvVGU','3nDzKulmSpg','r3WS1BOpgk4','j3Aa1dgg8UI','FAI2wj2JGCI','UCQHgJ4uRwo','SmQhRHS9-YA','mcnFWBLrdCs','Xco5vbBmF5c','sAbU4fAqjZk','O-1FpjPP6_c','-_14Lhw0y1A','9WKzt9QEmD4','pDvBiB1waBk','nn1pbxe8bAI','o_nxIQTM_B0','3iM_06QeZi8','tJM0yIbg8iQ','OcVmaIlHZ1o','ax1csKKQnns','Cxzzg7L3Xgc']

def get_next_update_time():
    """다음 10분 단위 업데이트 시간 계산 (KST 기준)"""
    now = datetime.now(timezone(timedelta(hours=9)))
    # 현재 분의 10분 단위 나머지
    minute_remainder = now.minute % 10
    # 나머지가 0이면 다음 10분 단위(10분 추가), 아니면 다음 10분 단위로 올림
    if minute_remainder == 0:
        minutes_to_add = 10
    else:
        minutes_to_add = 10 - minute_remainder
    # 초와 마이크로초를 0으로 설정하고 분 추가
    next_update = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    return next_update

def fetch_batch_videos(video_ids_batch):
    """배치로 비디오 정보 가져오기 (최대 50개)"""
    API_KEY = 'AIzaSyAmmehmaqCrWbKFwO6HhWMvQNtbbMDDaPQ'
    videos = []
    
    if not video_ids_batch:
        return videos
    
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
                    thumbnails = item.get('snippet', {}).get('thumbnails', {})
                    thumbnail_url = thumbnails.get('medium', {}).get('url') or \
                                thumbnails.get('high', {}).get('url') or \
                                thumbnails.get('default', {}).get('url', '')
                    view_count_int = int(view_count)
                    
                    videos.append({
                        'title': video_name,
                        'view_count': format(view_count_int, ','),
                        'view_count_raw': view_count_int,
                        'thumbnail': thumbnail_url,  # API에서 가져오기
                        'video_id': video_id
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

def get_view_count(video_list):
    """비디오 조회수 가져오기 (배치 요청 + 병렬 처리)"""
    if not video_list:
        return []
    
    videos = []
    
    # 비디오 리스트를 50개씩 배치로 나누기 (YouTube API 제한)
    batch_size = 50
    batches = [video_list[i:i + batch_size] for i in range(0, len(video_list), batch_size)]
    
    # 병렬 처리로 여러 배치를 동시에 요청
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_batch = {executor.submit(fetch_batch_videos, batch): batch for batch in batches}
        
        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_videos = future.result()
                videos.extend(batch_videos)
            except Exception as e:
                print(f"배치 처리 오류: {e}")
    
    # 조회수 내림차순으로 정렬 (높은 조회수부터)
    videos.sort(key=lambda x: x['view_count_raw'], reverse=True)
    return videos

@app.route('/')
def main():
    mv_videos = get_view_count(MV_LIST)
    live_videos = get_view_count(LIVE_LIST)
    update_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
    next_update_time = get_next_update_time()
    server_time = datetime.now(timezone(timedelta(hours=9)))
    return render_template('main.html', 
                         mv_videos=mv_videos,
                         live_videos=live_videos,
                         update_time=update_time,
                         next_update_time=next_update_time.isoformat(),
                         server_time=server_time.isoformat())

@app.route('/api/update')
def update_data():
    mv_videos = get_view_count(MV_LIST)
    live_videos = get_view_count(LIVE_LIST)
    update_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
    next_update_time = get_next_update_time()
    server_time = datetime.now(timezone(timedelta(hours=9)))
    return jsonify({
        'mv_videos': mv_videos,
        'live_videos': live_videos,
        'update_time': update_time,
        'next_update_time': next_update_time.isoformat(),
        'server_time': server_time.isoformat()
    })

if __name__ == '__main__':
    app.run(port = 80, debug=True, host = '0.0.0.0')


