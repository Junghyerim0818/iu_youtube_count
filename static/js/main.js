let countdownTimer;
let updateTimer;
let nextUpdateTime = null;
let serverTimeOffset = 0; // 서버 시간과 클라이언트 시간의 차이
let currentTab = 'mv'; // 현재 선택된 탭 (mv 또는 live)
let currentSort = 'view_count'; // 현재 정렬 기준 (view_count 또는 published_at)

// 탭 전환 함수
function switchTab(tabName) {
    console.log('switchTab 호출:', tabName);
    currentTab = tabName;
    
    // 탭 버튼 활성화 상태 변경
    const allTabs = document.querySelectorAll('.tab-btn');
    console.log('찾은 탭 버튼 수:', allTabs.length);
    allTabs.forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.getElementById(`tab-${tabName}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        console.log('활성 탭 버튼 설정:', tabName);
    } else {
        console.error('탭 버튼을 찾을 수 없음:', `tab-${tabName}`);
    }
    
    // 섹션 표시/숨김
    const allSections = document.querySelectorAll('.video-section');
    console.log('찾은 섹션 수:', allSections.length);
    allSections.forEach(section => {
        section.classList.remove('active');
        section.style.display = 'none';
    });
    
    const activeSection = document.getElementById(`${tabName}-section`);
    if (activeSection) {
        activeSection.classList.add('active');
        activeSection.style.display = 'block';
        console.log('활성 섹션 표시:', tabName);
    } else {
        console.error('섹션을 찾을 수 없음:', `${tabName}-section`);
    }
    
    // 카테고리 라벨 업데이트
    const categoryLabel = document.getElementById('category-label');
    if (categoryLabel) {
        categoryLabel.textContent = tabName === 'mv' ? '뮤직비디오' : '라이브클립';
    }
    
    // 제목 카운트 업데이트
    updateTitleCount();
}

// 제목 카운트 업데이트 함수
function updateTitleCount() {
    const titleCount = document.getElementById('title-count');
    if (!titleCount || !window.INITIAL_DATA) return;
    
    let count = 0;
    if (currentTab === 'mv' && window.INITIAL_DATA.mv_videos) {
        count = window.INITIAL_DATA.mv_videos.length;
    } else if (currentTab === 'live' && window.INITIAL_DATA.live_videos) {
        count = window.INITIAL_DATA.live_videos.length;
    }
    
    if (count > 0) {
        titleCount.textContent = `${count}편`;
    } else {
        titleCount.textContent = '';
    }
}

// 정렬 함수
function sortVideos(videos, sortBy) {
    if (!videos || videos.length === 0) return videos;
    
    const sortedVideos = [...videos];
    if (sortBy === 'view_count') {
        return sortedVideos.sort((a, b) => (b.view_count_raw || 0) - (a.view_count_raw || 0));
    } else if (sortBy === 'published_at') {
        return sortedVideos.sort((a, b) => {
            // 게시일자 문자열을 직접 비교
            const dateA = a.published_at_raw || '';
            const dateB = b.published_at_raw || '';
            
            // 빈 문자열 처리
            if (!dateA && !dateB) return 0;
            if (!dateA) return 1;  // A가 없으면 뒤로
            if (!dateB) return -1; // B가 없으면 A를 앞으로
            
            // ISO 8601 형식 문자열을 직접 비교 (내림차순: 최신순)
            return dateB.localeCompare(dateA);
        });
    }
    return sortedVideos;
}

// 변화 차이 포맷 함수
function formatViewChange(change) {
    if (change === 0 || change === undefined || change === null) {
        return '';
    }
    const sign = change > 0 ? '+' : '';
    return `(${sign}${formatNumber(change)})`;
}

// 숫자 포맷 함수 (천 단위 구분)
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// 비디오 HTML 생성 함수
function createVideoHTML(video) {
    const publishedDate = video.published_at ? video.published_at.substring(0, 10) : '';
    const viewChange = video.view_count_change || 0;
    const changeText = formatViewChange(viewChange);
    
    // 변화 차이 클래스 결정
    let changeClass = 'zero';
    if (viewChange > 0) {
        changeClass = 'positive';
    } else if (viewChange < 0) {
        changeClass = 'negative';
    }
    
    return `
        <a href="https://www.youtube.com/watch?v=${video.video_id || ''}" target="_blank" rel="noopener noreferrer" class="video-item">
            <img src="${video.thumbnail || ''}" alt="${video.title || ''}" class="video-thumbnail" onerror="this.style.display='none'">
            <div class="video-info">
                <div class="video-title">${video.title || '제목 없음'}</div>
                <div class="video-details">
                    <div class="view-count">
                        조회수: ${video.view_count || '0'}회
                        ${changeText ? `<span class="view-change-inline ${changeClass}">${changeText}</span>` : ''}
                    </div>
                    ${publishedDate ? `<div class="published-date">게시일자: <span class="date-value">${publishedDate}</span></div>` : ''}
                </div>
            </div>
        </a>
    `;
}

// 비디오 목록 렌더링 함수
function renderVideos(videos, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('컨테이너를 찾을 수 없음:', containerId);
        return;
    }
    
    if (!videos || videos.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">데이터가 없습니다.</div>';
        return;
    }
    
    // 서버에서 이미 정렬된 데이터를 받지만, 클라이언트에서도 다시 정렬 (일관성 유지)
    const sortedVideos = sortVideos([...videos], currentSort);
    container.innerHTML = sortedVideos.map(video => createVideoHTML(video)).join('');
    console.log('비디오 렌더링 완료:', containerId, sortedVideos.length, '개, 정렬:', currentSort);
}

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
    
    // 데이터 업데이트 요청 (정렬은 클라이언트에서 수행)
    console.log('데이터 업데이트 요청');
    fetch('/api/update')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 오류: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('데이터 업데이트 완료:', data);
            
            // 뮤직비디오 데이터 업데이트
            if (data.mv_videos) {
                // 초기 데이터 업데이트
                if (window.INITIAL_DATA) {
                    window.INITIAL_DATA.mv_videos = data.mv_videos;
                }
                // 클라이언트에서 현재 정렬 기준으로 렌더링
                renderVideos(data.mv_videos, 'mv-container');
            }
            
            // 라이브클립 데이터 업데이트
            if (data.live_videos) {
                // 초기 데이터 업데이트
                if (window.INITIAL_DATA) {
                    window.INITIAL_DATA.live_videos = data.live_videos;
                }
                // 클라이언트에서 현재 정렬 기준으로 렌더링
                renderVideos(data.live_videos, 'live-container');
            }
            
            // 제목 카운트 업데이트
            updateTitleCount();
            
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

// 정렬 변경 시 데이터 재정렬 및 렌더링 (클라이언트에서만 수행)
function handleSortChange() {
    const sortSelect = document.getElementById('sort-select');
    if (!sortSelect) {
        console.error('정렬 선택 요소를 찾을 수 없음');
        return;
    }
    
    currentSort = sortSelect.value;
    console.log('정렬 변경:', currentSort);
    
    // 현재 탭에 따라 해당 데이터만 재정렬 (로컬 데이터로 빠른 반응, 서버 요청 없음)
    if (currentTab === 'mv' && window.INITIAL_DATA && window.INITIAL_DATA.mv_videos) {
        renderVideos(window.INITIAL_DATA.mv_videos, 'mv-container');
    } else if (currentTab === 'live' && window.INITIAL_DATA && window.INITIAL_DATA.live_videos) {
        renderVideos(window.INITIAL_DATA.live_videos, 'live-container');
    }
    
    // 서버 요청 없이 클라이언트에서만 정렬 수행 (업데이트 시간 변경 방지)
}

// 페이지 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded 이벤트 발생');
    
    // 초기 데이터 렌더링
    if (window.INITIAL_DATA) {
        console.log('초기 데이터 로드:', window.INITIAL_DATA);
        console.log('뮤직비디오 수:', window.INITIAL_DATA.mv_videos?.length || 0);
        console.log('라이브클립 수:', window.INITIAL_DATA.live_videos?.length || 0);
        
        renderVideos(window.INITIAL_DATA.mv_videos || [], 'mv-container');
        renderVideos(window.INITIAL_DATA.live_videos || [], 'live-container');
        
        // 초기 제목 카운트 업데이트
        updateTitleCount();
    }
    
    // 탭 버튼 이벤트 리스너 - 모든 탭 버튼에 이벤트 추가
    const tabButtons = document.querySelectorAll('.tab-btn');
    console.log('탭 버튼 찾기:', tabButtons.length);
    
    tabButtons.forEach((btn, index) => {
        console.log(`탭 버튼 ${index}:`, btn.id, btn.getAttribute('data-tab'));
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const tabName = this.getAttribute('data-tab');
            console.log('탭 클릭 이벤트:', tabName, this.id);
            if (tabName) {
                switchTab(tabName);
            }
        });
    });
    
    // 정렬 선택 이벤트 리스너
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            handleSortChange();
        });
        console.log('정렬 선택 이벤트 리스너 추가됨');
    } else {
        console.error('정렬 선택 요소를 찾을 수 없음');
    }
    
    // window.SERVER_DATA가 있으면 초기화 (HTML에서 전달받음)
    if (window.SERVER_DATA && window.SERVER_DATA.next_update_time && window.SERVER_DATA.server_time) {
        initializeCountdown(window.SERVER_DATA.next_update_time, window.SERVER_DATA.server_time);
    }
    
    // 초기 탭 설정 - 약간의 지연을 두고 실행
    setTimeout(() => {
        console.log('초기 탭 설정: mv');
        switchTab('mv');
    }, 100);
    
    console.log('초기화 완료');
});

// 추가: 디버깅을 위한 전역 함수
window.debugTabs = function() {
    console.log('현재 탭:', currentTab);
    console.log('현재 정렬:', currentSort);
    console.log('뮤직비디오 섹션:', document.getElementById('mv-section'));
    console.log('라이브클립 섹션:', document.getElementById('live-section'));
    console.log('탭 버튼들:', document.querySelectorAll('.tab-btn'));
    console.log('초기 데이터:', window.INITIAL_DATA);
};
