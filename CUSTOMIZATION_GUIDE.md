# Customization Guide
## AI-Driven Emergency Ambulance Routing System Landing Page

A comprehensive guide for customizing and extending the landing page.

---

## 📋 Quick Customization Checklist

- [ ] Update project name and descriptions
- [ ] Change colors to match your brand
- [ ] Update contact information
- [ ] Replace placeholder images
- [ ] Add actual demo video link
- [ ] Update statistics and metrics
- [ ] Add team information
- [ ] Configure analytics
- [ ] Set up email integration
- [ ] Test on mobile devices

---

## 🎨 Color Customization

### Step 1: Update CSS Variables
Edit the `:root` section in `styles.css` (lines 1-13):

```css
:root {
    --primary: #dc3545;           /* Primary brand color */
    --medical-red: #e74c3c;       /* Medical/emergency color */
    --hospital-blue: #2c3e50;     /* Trust/professional color */
    --light-bg: #f5f7fa;          /* Light background */
}
```

### Step 2: Update Bootstrap Theme Color
Replace all `.btn-danger` and `.text-danger` classes or update Bootstrap's default:

```html
<!-- In the <head> section -->
<style>
    :root {
        --bs-danger: #your-new-color;
    }
</style>
```

### Color Palette Suggestions
- **Medical/Emergency**: Red (#e74c3c), Crimson (#c92a2a)
- **Healthcare Trust**: Blue (#0084d6), Teal (#087e8b)
- **Modern Professional**: Gray (#2c3e50), Dark (#1a1a1a)

---

## ✏️ Content Customization

### Hero Section (Lines 66-96)
```html
<h1 class="display-3 fw-800 mb-4 text-dark">
    Your Custom Title Here
</h1>
<p class="lead text-muted mb-4">
    Your custom description here
</p>
```

### Update Statistics (Lines 86-96)
```html
<div class="stat-item">
    <h3 class="text-danger fw-bold">YOUR-NUMBER%</h3>
    <p class="text-muted">Your metric here</p>
</div>
```

### Features Section (Lines 108-170)
Update feature cards with your specific features:
```html
<div class="feature-card h-100">
    <div class="feature-icon bg-danger-light">
        <i class="fas fa-your-icon text-danger"></i>
    </div>
    <h3 class="fw-700 mt-3">Your Feature Title</h3>
    <p class="text-muted">Your feature description</p>
</div>
```

### Process Steps (Lines 180-225)
Replace the 4-step process with your specific workflow:
```html
<div class="process-step active">
    <div class="step-number">1</div>
    <div class="step-content">
        <h4 class="fw-700">Your Step Title</h4>
        <p class="text-muted">Your step description</p>
    </div>
</div>
```

### Benefits Section (Lines 237-300)
Update with your unique benefits:
```html
<div class="benefit-item d-flex gap-4">
    <div class="benefit-icon flex-shrink-0">
        <i class="fas fa-your-icon text-danger"></i>
    </div>
    <div>
        <h5 class="fw-700 mb-2">Benefit Title</h5>
        <p class="text-muted">Benefit description</p>
    </div>
</div>
```

### Technology Stack (Lines 315-365)
Add your actual technologies:
```html
<div class="tech-card">
    <div class="tech-icon">
        <i class="fas fa-your-tech text-danger"></i>
    </div>
    <h5 class="fw-700 mt-3">Technology Name</h5>
    <p class="text-muted small">Technology description</p>
</div>
```

### Contact Information (Lines 425-439)
Update footer contact details:
```html
<li><i class="fas fa-envelope me-2"></i>your-email@example.com</li>
<li><i class="fas fa-phone me-2"></i>+1 (YOUR) NUMBER</li>
<li><i class="fas fa-map-marker-alt me-2"></i>Your Address</li>
```

---

## 🖼️ Media Customization

### Replace Placeholder Images
In the "How It Works" section (line 224):
```html
<!-- OLD -->
<img src="https://via.placeholder.com/400x300?text=Process+Flow" alt="Process Flow" class="img-fluid rounded-3">

<!-- NEW -->
<img src="path/to/your/image.jpg" alt="Process Flow" class="img-fluid rounded-3">
```

### Optimize Images
Before uploading:
1. Compress images (use TinyPNG or similar)
2. Use WebP format for better compression
3. Keep dimensions at 2x size (e.g., 800x600 for 400x300 display)
4. Always include descriptive alt text

### Add Icons
Font Awesome is already loaded. Browse available icons at:
https://fontawesome.com/icons

Usage:
```html
<i class="fas fa-icon-name"></i>         <!-- Solid -->
<i class="far fa-icon-name"></i>         <!-- Regular -->
<i class="fab fa-icon-name"></i>         <!-- Brands -->
```

---

## 🎬 Demo Video Integration

### Update Demo Modal (Lines 359-372)
Replace YouTube video ID:
```html
<!-- OLD -->
<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" ...></iframe>

<!-- NEW -->
<iframe src="https://www.youtube.com/embed/YOUR-VIDEO-ID" ...></iframe>
```

### Alternative Video Platforms
```html
<!-- Vimeo -->
<iframe src="https://player.vimeo.com/video/VIDEO-ID" ...></iframe>

<!-- Local video file -->
<video controls width="100%">
    <source src="demo.mp4" type="video/mp4">
</video>
```

---

## 🔤 Font Customization

### Change Font Family
Edit Google Fonts import in `index.html` (line 12):
```html
<!-- Add new fonts -->
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Montserrat&display=swap" rel="stylesheet">
```

Update CSS in `styles.css`:
```css
body {
    font-family: 'Roboto', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif;
}
```

### Font Weight Classes
- `.fw-300`: Light
- `.fw-400`: Normal
- `.fw-500`: Medium
- `.fw-600`: Semi-bold
- `.fw-700`: Bold
- `.fw-800`: Extra-bold

---

## 🔗 Link & Navigation Customization

### Update Navigation Links (Lines 23-31)
Add or modify navigation items:
```html
<li class="nav-item"><a class="nav-link" href="#your-section">Your Section</a></li>
```

### Update Footer Links (Lines 448-460)
Modify footer navigation:
```html
<li><a href="#section" class="text-muted text-decoration-none">Link Text</a></li>
```

### Add Social Media Links (Lines 471-477)
```html
<a href="https://twitter.com/yourhandle" class="text-muted text-decoration-none me-3">
    <i class="fab fa-twitter"></i>
</a>
```

---

## 🎞️ Animation Customization

### Adjust Fade-In Animation
In `styles.css`:
```css
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);  /* Adjust distance */
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

### Modify Floating Animation
```css
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }  /* Adjust height */
}
```

### Change Process Step Auto-Cycle Time
In `script.js` (line 98):
```javascript
setInterval(function() {
    // ... code ...
}, 5000);  /* Change to desired milliseconds */
```

### Disable Auto-Cycling
Comment out the entire `setInterval` block in `script.js`.

---

## 📱 Responsive Design Adjustments

### Modify Mobile Breakpoint
In `styles.css`, find media queries and adjust breakpoints:
```css
@media (max-width: 992px) {  /* Change from 1024px */
    /* Mobile styles */
}
```

### Adjust Padding for Mobile
```css
.py-6 {
    padding-top: 5rem !important;      /* Desktop */
    padding-bottom: 5rem !important;
}

@media (max-width: 768px) {
    .py-6 {
        padding-top: 2rem !important;   /* Mobile - adjust as needed */
        padding-bottom: 2rem !important;
    }
}
```

---

## 🔐 Form Integration

### Add Contact Form
Replace the "Get Started" button with a form:
```html
<form id="contactForm" method="POST" action="your-backend-endpoint">
    <div class="mb-3">
        <input type="email" class="form-control" name="email" required>
    </div>
    <div class="mb-3">
        <textarea class="form-control" name="message" required></textarea>
    </div>
    <button type="submit" class="btn btn-danger">Submit</button>
</form>
```

### Handle Form Submission
Update `script.js`:
```javascript
document.getElementById('contactForm').addEventListener('submit', function(e) {
    e.preventDefault();
    // Send to backend or email service
    console.log('Form submitted');
});
```

---

## 📊 Analytics Integration

### Add Google Analytics
Add before closing `</head>` tag:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA-ID"></script>
<script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'GA-YOUR-ID');
</script>
```

### Track Button Clicks
Add to `script.js`:
```javascript
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function() {
        gtag('event', 'button_click', {
            'button_text': this.textContent
        });
    });
});
```

---

## 🌍 SEO Optimization

### Update Meta Tags
In `index.html` `<head>`:
```html
<meta name="description" content="Your description here">
<meta name="keywords" content="keyword1, keyword2, keyword3">
<meta name="author" content="Your Name">
<meta property="og:title" content="Your Page Title">
<meta property="og:description" content="Your description">
<meta property="og:image" content="image-url">
```

### Add Structured Data
```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "AI Ambulance Routing System",
    "description": "Your description",
    "organization": {
        "@type": "Organization",
        "name": "Your Company",
        "logo": "logo-url"
    }
}
</script>
```

---

## 🧪 Testing Checklist

- [ ] Test on Chrome, Firefox, Safari, Edge
- [ ] Test on iPhone, iPad, Android devices
- [ ] Check accessibility with keyboard navigation
- [ ] Verify all links work correctly
- [ ] Test form submissions
- [ ] Check image loading
- [ ] Verify video embedding
- [ ] Test smooth scrolling
- [ ] Check navbar responsiveness
- [ ] Verify button hover effects

---

## 📋 Deployment Checklist

Before deploying:
- [ ] Update all placeholder text
- [ ] Replace all placeholder images
- [ ] Test all interactive features
- [ ] Optimize images for web
- [ ] Minify CSS and JavaScript (optional)
- [ ] Update meta tags and title
- [ ] Configure analytics
- [ ] Set up form backend
- [ ] Test form submissions
- [ ] Check mobile responsiveness
- [ ] Verify all external links
- [ ] Set up 404 error handling
- [ ] Enable HTTPS/SSL
- [ ] Create sitemap.xml
- [ ] Submit to search engines

---

## 🚀 Advanced Customizations

### Add Dark Mode
Create dark mode styles in `styles.css`:
```css
@media (prefers-color-scheme: dark) {
    body {
        background-color: #1a1a1a;
        color: #f0f0f0;
    }
    /* ... update colors */
}
```

### Add Newsletter Subscription
```html
<div class="newsletter-signup">
    <form id="newsletterForm">
        <input type="email" placeholder="Enter your email" required>
        <button type="submit">Subscribe</button>
    </form>
</div>
```

### Add Testimonials Section
```html
<section id="testimonials" class="py-6">
    <div class="container-lg">
        <div class="row">
            <div class="col-md-4">
                <div class="testimonial-card">
                    <p class="quote">"Quote here"</p>
                    <p class="author">- Hospital Name</p>
                </div>
            </div>
        </div>
    </div>
</section>
```

---

## 🐛 Troubleshooting

### Videos Not Playing
- Check video URL is correct
- Verify permissions allow embedding
- Try different video platform

### Images Not Loading
- Verify image file path is correct
- Check file exists in directory
- Verify CORS permissions for external images

### Styles Not Applied
- Check for typos in CSS class names
- Verify CSS file is linked correctly
- Clear browser cache (Ctrl+Shift+Delete)

### JavaScript Not Working
- Open browser console (F12) for errors
- Check internet connection for CDN resources
- Verify script.js is loaded
- Check Bootstrap JS is after jQuery (if used)

---

## 📞 Support & Resources

### Documentation Links
- Bootstrap Docs: https://getbootstrap.com/docs/5.3/
- Font Awesome: https://fontawesome.com/docs
- Google Fonts: https://fonts.google.com/
- MDN Web Docs: https://developer.mozilla.org/

### Tools & Services
- Figma: Design mockups
- TinyPNG: Image compression
- Lighthouse: Performance testing
- WAVE: Accessibility checking

---

**Last Updated**: February 20, 2026

For more help, refer to the main README.md file or consult the code comments in individual files.
