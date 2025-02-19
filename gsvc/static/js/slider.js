document.addEventListener('DOMContentLoaded', function() {
    // Get all comparison containers
    const comparisonContainers = document.querySelectorAll('.comparison-container');
    
    // Initialize each comparison slider
    comparisonContainers.forEach((container, index) => {
        initializeComparisonSlider(container, index);
    });
    
    function initializeComparisonSlider(container, index) {
        // Get elements
        const videoWrapper = container.querySelector('.video-wrapper');
        const slider = container.querySelector('.slider-handle');
        const videoBefore = container.querySelector('.video-before');
        const videoAfter = container.querySelector('.video-after');
        const playPauseBtn = container.querySelector('.play-pause-btn');
        const resetBtn = container.querySelector('.reset-btn');
        
        // Generate unique ID for CSS variables
        const sliderId = `slider-${index}`;
        videoWrapper.dataset.sliderId = sliderId;
        
        // Set initial slider position (vary slightly for visual interest)
        const initialPositions = [50, 40, 60];
        let sliderPosition = initialPositions[index % initialPositions.length];
        updateSliderPosition(sliderPosition);
        
        // Event listeners for slider dragging
        let isDragging = false;
        
        slider.addEventListener('mousedown', startDrag);
        slider.addEventListener('touchstart', startDrag, { passive: true });
        
        function startDrag(e) {
            e.preventDefault();
            isDragging = true;
            
            // Add global move and end event listeners
            document.addEventListener('mousemove', drag);
            document.addEventListener('touchmove', drag, { passive: false });
            document.addEventListener('mouseup', endDrag);
            document.addEventListener('touchend', endDrag);
        }
        
        function drag(e) {
            if (!isDragging) return;
            
            e.preventDefault();
            const containerRect = videoWrapper.getBoundingClientRect();
            
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
            if (isDragging) {
                isDragging = false;
                // Remove global listeners
                document.removeEventListener('mousemove', drag);
                document.removeEventListener('touchmove', drag);
                document.removeEventListener('mouseup', endDrag);
                document.removeEventListener('touchend', endDrag);
            }
        }
        
        function updateSliderPosition(position) {
            // Use inline style for the clip-path to ensure each slider works independently
            videoBefore.style.clipPath = `polygon(0 0, ${position}% 0, ${position}% 100%, 0 100%)`;
            slider.style.left = `${position}%`;
        }
        
        // Play/Pause button
        playPauseBtn.addEventListener('click', togglePlayPause);
        
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
        
        // Reset button
        resetBtn.addEventListener('click', resetVideos);
        
        function resetVideos() {
            videoBefore.currentTime = 0;
            videoAfter.currentTime = 0;
            if (!videoBefore.paused) {
                videoBefore.play();
                videoAfter.play();
            }
            // Reset slider to initial position
            sliderPosition = initialPositions[index % initialPositions.length];
            updateSliderPosition(sliderPosition);
        }
        
        // Video synchronization
        videoBefore.addEventListener('play', syncVideos);
        videoAfter.addEventListener('play', syncVideos);
        
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
        
        // Optional: Intersection Observer to manage video playback when visible
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Only autoplay if the page hasn't been interacted with yet
                    if (playPauseBtn.textContent === 'Play') {
                        // Optional: uncomment to autoplay when scrolled into view
                        // togglePlayPause();
                    }
                } else {
                    // Pause when not visible
                    if (!videoBefore.paused) {
                        videoBefore.pause();
                        videoAfter.pause();
                        playPauseBtn.textContent = 'Play';
                    }
                }
            });
        }, { threshold: 0.4 });
        
        observer.observe(videoWrapper);
    }
});