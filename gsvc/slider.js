document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const container = document.querySelector('.video-wrapper');
    const slider = document.querySelector('.slider-handle');
    const videoBefore = document.getElementById('video-before');
    const videoAfter = document.getElementById('video-after');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    
    // Set initial slider position
    let sliderPosition = 50;
    updateSliderPosition(sliderPosition);
    
    // Event listeners for slider dragging
    let isDragging = false;
    
    slider.addEventListener('mousedown', startDrag);
    slider.addEventListener('touchstart', startDrag, { passive: true });
    
    document.addEventListener('mousemove', drag);
    document.addEventListener('touchmove', drag, { passive: false });
    
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchend', endDrag);
    
    // Play/Pause button
    playPauseBtn.addEventListener('click', togglePlayPause);
    
    // Reset button
    resetBtn.addEventListener('click', resetVideos);
    
    // Video synchronization
    videoBefore.addEventListener('play', syncVideos);
    videoAfter.addEventListener('play', syncVideos);
    
    // Functions
    function startDrag(e) {
        e.preventDefault();
        isDragging = true;
    }
    
    function drag(e) {
        if (!isDragging) return;
        
        e.preventDefault();
        const containerRect = container.getBoundingClientRect();
        
        let clientX;
        if (e.type === 'touchmove') {
            clientX = e.touches[0].clientX;
        } else {
            clientX = e.clientX;
        }
        
        const containerX = clientX - containerRect.left;
        sliderPosition = (containerX / containerRect.width) * 100;
        
        // Constrain slider position
        sliderPosition = Math.max(0, Math.min(100, sliderPosition));
        
        updateSliderPosition(sliderPosition);
    }
    
    function endDrag() {
        isDragging = false;
    }
    
    function updateSliderPosition(position) {
        container.style.setProperty('--slider-position', `${position}%`);
        slider.style.left = `${position}%`;
    }
    
    function togglePlayPause() {
        if (videoBefore.paused || videoAfter.paused) {
            videoBefore.play();
            videoAfter.play();
            playPauseBtn.textContent = 'Pause';
        } else {
            videoBefore.pause();
            videoAfter.pause();
            playPauseBtn.textContent = 'Play';
        }
    }
    
    function resetVideos() {
        videoBefore.currentTime = 0;
        videoAfter.currentTime = 0;
        if (!videoBefore.paused) {
            videoBefore.play();
            videoAfter.play();
        }
        // Reset slider to middle
        sliderPosition = 50;
        updateSliderPosition(sliderPosition);
    }
    
    function syncVideos() {
        // Keep videos in sync when playing
        if (!videoBefore.paused) {
            videoAfter.currentTime = videoBefore.currentTime;
            videoAfter.play();
        }
        if (!videoAfter.paused) {
            videoBefore.currentTime = videoAfter.currentTime;
            videoBefore.play();
        }
    }
    
    // Optional: Auto-play videos when they're visible
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                resetVideos();
                if (playPauseBtn.textContent === 'Pause') {
                    videoBefore.play();
                    videoAfter.play();
                }
            } else {
                videoBefore.pause();
                videoAfter.pause();
            }
        });
    }, { threshold: 0.5 });
    
    observer.observe(container);
});