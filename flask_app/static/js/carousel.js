/**
 * Product Carousel Component
 * Features: Navigation, Autoplay, Touch/Swipe, Responsive
 */

class ProductCarousel {
  constructor(carouselElement) {
    this.carousel = carouselElement;
    this.carouselId = carouselElement.id;
    this.track = carouselElement.querySelector('.carousel-track');
    this.items = Array.from(carouselElement.querySelectorAll('.carousel-item'));
    
    this.currentIndex = 0;
    this.itemWidth = 0;
    this.itemsPerView = this.getItemsPerView();
    this.autoplayEnabled = carouselElement.dataset.autoplay === 'true';
    this.autoplayDelay = parseInt(carouselElement.dataset.autoplayDelay || 5000);
    this.autoplayInterval = null;
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragCurrentX = 0;
    
    this.init();
  }

  init() {
    this.attachEventListeners();
    this.updateItemWidth();
    this.startAutoplay();
    window.addEventListener('resize', () => this.handleResize());
  }

  attachEventListeners() {
    // Navigation buttons
    const prevBtn = document.querySelector(`.carousel-prev[data-carousel="${this.carouselId}"]`);
    const nextBtn = document.querySelector(`.carousel-next[data-carousel="${this.carouselId}"]`);

    if (prevBtn) prevBtn.addEventListener('click', () => this.prev());
    if (nextBtn) nextBtn.addEventListener('click', () => this.next());

    // Touch/Swipe support
    this.carousel.addEventListener('touchstart', (e) => this.handleTouchStart(e), false);
    this.carousel.addEventListener('touchmove', (e) => this.handleTouchMove(e), false);
    this.carousel.addEventListener('touchend', (e) => this.handleTouchEnd(e), false);

    // Mouse drag support
    this.carousel.addEventListener('mousedown', (e) => this.handleMouseDown(e), false);
    this.carousel.addEventListener('mousemove', (e) => this.handleMouseMove(e), false);
    this.carousel.addEventListener('mouseup', (e) => this.handleMouseUp(e), false);
    this.carousel.addEventListener('mouseleave', (e) => this.handleMouseUp(e), false);

    // Pause autoplay on interaction
    this.carousel.addEventListener('mouseenter', () => this.pauseAutoplay());
    this.carousel.addEventListener('mouseleave', () => this.resumeAutoplay());
  }

  getItemsPerView() {
    const width = window.innerWidth;
    if (width >= 1025) return 4;      // Desktop: 4 items
    if (width >= 769) return 3;       // Tablet: 3 items
    if (width >= 481) return 2;       // Mobile: 2 items
    return 1;                          // Small Mobile: 1 item
  }

  updateItemWidth() {
    if (this.items.length === 0) return;
    
    const containerWidth = this.carousel.offsetWidth;
    const gap = 24; // 1.5rem in pixels
    
    this.itemsPerView = this.getItemsPerView();
    this.itemWidth = (containerWidth - gap * (this.itemsPerView - 1)) / this.itemsPerView;
    
    this.updateTrackPosition();
  }

  updateTrackPosition() {
    const totalGap = 24 * (this.itemsPerView - 1);
    const offset = -(this.currentIndex * (this.itemWidth + 24));
    this.track.style.transform = `translateX(${offset}px)`;
  }

  next() {
    const maxIndex = Math.max(0, this.items.length - this.itemsPerView);
    if (this.currentIndex < maxIndex) {
      this.currentIndex++;
    } else {
      // Loop back to start
      this.currentIndex = 0;
    }
    this.updateTrackPosition();
    this.resetAutoplay();
  }

  prev() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
    } else {
      // Loop to end
      const maxIndex = Math.max(0, this.items.length - this.itemsPerView);
      this.currentIndex = maxIndex;
    }
    this.updateTrackPosition();
    this.resetAutoplay();
  }

  handleTouchStart(e) {
    this.isDragging = true;
    this.dragStartX = e.touches[0].clientX;
    this.pauseAutoplay();
  }

  handleTouchMove(e) {
    if (!this.isDragging) return;
    this.dragCurrentX = e.touches[0].clientX;
  }

  handleTouchEnd(e) {
    if (!this.isDragging) return;
    this.isDragging = false;

    const diff = this.dragStartX - this.dragCurrentX;
    const threshold = 50; // Minimum drag distance

    if (Math.abs(diff) > threshold) {
      if (diff > 0) {
        this.next(); // Swipe left = next
      } else {
        this.prev(); // Swipe right = prev
      }
    }

    this.resumeAutoplay();
  }

  handleMouseDown(e) {
    if (e.button !== 0) return; // Only left click
    this.isDragging = true;
    this.dragStartX = e.clientX;
    this.pauseAutoplay();
    this.track.style.cursor = 'grabbing';
  }

  handleMouseMove(e) {
    if (!this.isDragging) return;
    this.dragCurrentX = e.clientX;
  }

  handleMouseUp(e) {
    if (!this.isDragging) return;
    this.isDragging = false;
    this.track.style.cursor = 'grab';

    const diff = this.dragStartX - this.dragCurrentX;
    const threshold = 30;

    if (Math.abs(diff) > threshold) {
      if (diff > 0) {
        this.next();
      } else {
        this.prev();
      }
    }

    this.resumeAutoplay();
  }

  startAutoplay() {
    if (!this.autoplayEnabled) return;
    this.autoplayInterval = setInterval(() => this.next(), this.autoplayDelay);
  }

  pauseAutoplay() {
    if (this.autoplayInterval) {
      clearInterval(this.autoplayInterval);
      this.autoplayInterval = null;
    }
  }

  resumeAutoplay() {
    if (this.autoplayEnabled && !this.autoplayInterval) {
      this.startAutoplay();
    }
  }

  resetAutoplay() {
    this.pauseAutoplay();
    this.startAutoplay();
  }

  handleResize() {
    const newItemsPerView = this.getItemsPerView();
    if (newItemsPerView !== this.itemsPerView) {
      this.currentIndex = 0;
      this.updateItemWidth();
    }
  }

  destroy() {
    this.pauseAutoplay();
    window.removeEventListener('resize', () => this.handleResize());
  }
}

/**
 * Initialize all carousels on page load
 */
document.addEventListener('DOMContentLoaded', () => {
  const carouselElements = document.querySelectorAll('.carousel-container');
  const carousels = [];

  carouselElements.forEach((element) => {
    const carousel = new ProductCarousel(element);
    carousels.push(carousel);
  });

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    carousels.forEach((carousel) => carousel.destroy());
  });
});

/**
 * Utility: Lazy load carousel on scroll into view
 */
if ('IntersectionObserver' in window) {
  const carouselObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('carousel-loaded');
        observer.unobserve(entry.target);
      }
    });
  }, {
    rootMargin: '50px'
  });

  document.querySelectorAll('.carousel-section').forEach((section) => {
    carouselObserver.observe(section);
  });
}
