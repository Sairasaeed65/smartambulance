/* ================================================== */
/*    SMARTAMBULANCE - APPLICATION JAVASCRIPT        */
/*          Smooth Scrolling & Utilities             */
/* ================================================== */

'use strict';

/**
 * Initialize application on DOM ready
 * Sets up smooth scrolling and event listeners
 */
document.addEventListener('DOMContentLoaded', function() {
    initSmoothScroll();
    initLoginModal();
    initEmergencyButton();
    logApplicationInfo();
});

/**
 * Initialize smooth scrolling for anchor links
 * - Navigation links scroll smoothly to target sections
 * - Navbar collapses after link click on mobile
 */
function initSmoothScroll() {
    const navLinks = document.querySelectorAll('a[href^="#"]');
    
    navLinks.forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            // Skip if not a valid anchor
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (!target) return;
            
            e.preventDefault();
            
            // Smooth scroll to target section
            target.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
            
            // Close mobile navbar if open
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                navbarCollapse.classList.remove('show');
            }
        });
    });
}

/**
 * Log application information to console
 * Useful for development and debugging
 */
function logApplicationInfo() {
    console.log(
        '%cSmartAmbulance - Emergency Routing System',
        'font-size: 14px; color: #00d4ff; font-weight: bold;'
    );
    console.log(
        '%cAI-Driven Emergency Ambulance Routing for Fast, Intelligent, Life-Saving Response',
        'font-size: 11px; color: #a0a8b8; font-style: italic;'
    );
}

/**
 * Initialize login modal functionality
 * - Auto-collapse navbar when login button is clicked
 * - Handle modal interactions
 */
function initLoginModal() {
    const loginButton = document.querySelector('[data-bs-target="#loginModal"]');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (loginButton) {
        loginButton.addEventListener('click', function() {
            // Close mobile navbar if open
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                navbarCollapse.classList.remove('show');
            }
        });
    }
}

/**
 * Trigger emergency sequence
 * - Change button text and color
 * - Fade out page
 * - Redirect to emergency page
 */
function triggerEmergency() {
    const emergencyBtn = document.querySelector('.btn-emergency');
    
    if (!emergencyBtn || emergencyBtn.getAttribute('data-activating') === 'true') {
        return; // Prevent multiple clicks
    }
    
    // Mark button as activating
    emergencyBtn.setAttribute('data-activating', 'true');
    
    // Change button text
    emergencyBtn.textContent = 'CONNECTING TO EMERGENCY SYSTEM...';
    
    // Add animation classes
    emergencyBtn.classList.add('activating');
    
    // Create and show overlay
    const overlay = document.createElement('div');
    overlay.className = 'emergency-overlay';
    document.body.appendChild(overlay);
    
    // Trigger overlay animation after a brief delay
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
    
    // Redirect to emergency page after animation completes (1.5 seconds)
    setTimeout(() => {
        window.location.href = '/emergency';
    }, 1500);
}

/**
 * Initialize emergency button functionality
 * - Navigate to emergency page when clicked
 * - Works for both authenticated and non-authenticated users
 */
function initEmergencyButton() {
    const emergencyBtn = document.querySelector('.btn-emergency');
    
    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', triggerEmergency);
}
