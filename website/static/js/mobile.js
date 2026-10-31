// Mobile Navigation Drawer Toggle
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menuToggle');
    const mobileDrawer = document.getElementById('mobileDrawer');
    const mobileBackdrop = document.getElementById('mobileBackdrop');
    const drawerClose = document.getElementById('drawerClose');

    function openDrawer() {
        if (mobileDrawer) mobileDrawer.classList.add('open');
        if (mobileBackdrop) mobileBackdrop.classList.add('open');
        if (menuToggle) menuToggle.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        if (mobileDrawer) mobileDrawer.classList.remove('open');
        if (mobileBackdrop) mobileBackdrop.classList.remove('open');
        if (menuToggle) menuToggle.classList.remove('open');
        document.body.style.overflow = '';
    }

    if (menuToggle) {
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (mobileDrawer && mobileDrawer.classList.contains('open')) {
                closeDrawer();
            } else {
                openDrawer();
            }
        });
    }

    if (drawerClose) {
        drawerClose.addEventListener('click', closeDrawer);
    }

    if (mobileBackdrop) {
        mobileBackdrop.addEventListener('click', closeDrawer);
    }

    // Touch Swipe gestures for room sliders
    const sliders = document.querySelectorAll('.room-slider');
    sliders.forEach(slider => {
        let startX = 0;
        let endX = 0;
        slider.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        }, { passive: true });

        slider.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            const diff = startX - endX;
            const sliderId = slider.id;
            if (Math.abs(diff) > 40 && typeof moveSlide === 'function') {
                if (diff > 0) {
                    moveSlide(sliderId, 1); // Swipe left -> Next slide
                } else {
                    moveSlide(sliderId, -1); // Swipe right -> Prev slide
                }
            }
        }, { passive: true });
    });
});
