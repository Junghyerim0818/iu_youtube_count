let countdownTimer;
let updateTimer;
let nextUpdateTime = null;
let serverTimeOffset = 0; // 서버 시간과 클라이언트 시간의 차이

function formatTime(seconds) {
    if (seconds < 0) return '00:00';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateCountdown() {
    if (!nextUpdateTime) return;
    
    const countdownElement = document.getElementById('countdown');
    if (!countdownElement) return;
    
    const now = new Date();
    // 서버 시간 기준으로 계산 (클라이언트 시간 + 오프셋)
    const serverNow = new Date(now.getTime() + serverTimeOffset);
    const nextUpdate = new Date(nextUpdateTime);
    const diff = Math.floor((nextUpdate - serverNow) / 1000);
    
    countdownElement.textContent = formatTime(diff);
    
    // 다음 업데이트 시간이 지났으면 데이터 업데이트
    if (diff <= 0) {
        updateData();
    }
}

function initializeCountdown(nextUpdateTimeISO, serverTimeISO) {
    nextUpdateTime = nextUpdateTimeISO;
    const serverTime = new Date(serverTimeISO);
    const clientTime = new Date();
    // 서버 시간과 클라이언트 시간의 차이 계산
    serverTimeOffset = serverTime - clientTime;
    
    // 카운트다운 시작 (1초마다 업데이트)
    clearInterval(countdownTimer);
    updateCountdown();
    countdownTimer = setInterval(updateCountdown, 1000);
}

function updateData() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    
    fetch('/api/update')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 오류: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // 뮤직비디오 데이터 업데이트
            const mvContainer = document.getElementById('mv-container');
            if (mvContainer && data.mv_videos) {
                mvContainer.innerHTML = data.mv_videos.map(video => `
                    <div class="video-item">
                        <a href="https://www.youtube.com/watch?v=${video.video_id || ''}" target="_blank" rel="noopener noreferrer">
                            <img src="${video.thumbnail || ''}" alt="${video.title || ''}" class="video-thumbnail" onerror="this.style.display='none'">
                        </a>
                        <div class="video-info">
                            <div class="video-title">${video.title || '제목 없음'}</div>
                            <div class="view-count">조회수: ${video.view_count || '0'}회</div>
                        </div>
                    </div>
                `).join('');
            }
            
            // 라이브클립 데이터 업데이트
            const liveContainer = document.getElementById('live-container');
            if (liveContainer && data.live_videos) {
                liveContainer.innerHTML = data.live_videos.map(video => `
                    <div class="video-item">
                        <a href="https://www.youtube.com/watch?v=${video.video_id || ''}" target="_blank" rel="noopener noreferrer">
                            <img src="${video.thumbnail || ''}" alt="${video.title || ''}" class="video-thumbnail" onerror="this.style.display='none'">
                        </a>
                        <div class="video-info">
                            <div class="video-title">${video.title || '제목 없음'}</div>
                            <div class="view-count">조회수: ${video.view_count || '0'}회</div>
                        </div>
                    </div>
                `).join('');
            }
            
            // 업데이트 시간 업데이트
            const updateTimeElement = document.getElementById('update-time');
            if (updateTimeElement && data.update_time) {
                updateTimeElement.textContent = data.update_time;
            }
            
            // 다음 업데이트 시간 설정 및 카운트다운 재시작
            if (data.next_update_time && data.server_time) {
                initializeCountdown(data.next_update_time, data.server_time);
            }
            
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('업데이트 실패:', error);
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
        });
}

// 페이지 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    // window.SERVER_DATA가 있으면 초기화 (HTML에서 전달받음)
    if (window.SERVER_DATA && window.SERVER_DATA.next_update_time && window.SERVER_DATA.server_time) {
        initializeCountdown(window.SERVER_DATA.next_update_time, window.SERVER_DATA.server_time);
    }
});
