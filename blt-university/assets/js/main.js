// BLT University JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // Course Filtering
    const categoryFilter = document.getElementById('category-filter');
    const levelFilter = document.getElementById('level-filter');
    const searchFilter = document.getElementById('search-filter');
    const coursesGrid = document.getElementById('courses-grid');
    const noResults = document.getElementById('no-results');
    
    if (categoryFilter && levelFilter && searchFilter && coursesGrid) {
        function filterCourses() {
            const categoryValue = categoryFilter.value.toLowerCase();
            const levelValue = levelFilter.value.toLowerCase();
            const searchValue = searchFilter.value.toLowerCase();
            
            const courses = coursesGrid.getElementsByClassName('course-card');
            let visibleCount = 0;
            
            Array.from(courses).forEach(course => {
                const courseCategory = course.getAttribute('data-category');
                const courseLevel = course.getAttribute('data-level');
                const courseSearch = course.getAttribute('data-search');
                
                const categoryMatch = !categoryValue || courseCategory === categoryValue;
                const levelMatch = !levelValue || courseLevel === levelValue;
                const searchMatch = !searchValue || courseSearch.includes(searchValue);
                
                if (categoryMatch && levelMatch && searchMatch) {
                    course.style.display = '';
                    visibleCount++;
                } else {
                    course.style.display = 'none';
                }
            });
            
            if (noResults) {
                noResults.style.display = visibleCount === 0 ? 'block' : 'none';
            }
        }
        
        categoryFilter.addEventListener('change', filterCourses);
        levelFilter.addEventListener('change', filterCourses);
        searchFilter.addEventListener('input', filterCourses);
    }
    
    // Parse URL parameters for enrollment
    const urlParams = new URLSearchParams(window.location.search);
    const courseParam = urlParams.get('course');
    const titleParam = urlParams.get('title');
    
    if (courseParam && window.location.pathname.includes('/enroll/')) {
        console.log('Enrolling in course:', courseParam, titleParam);
        
        // Update the enrollment button to prefill the title if available
        if (titleParam) {
            const enrollButton = document.querySelector('[data-enrollment-button]');
            if (enrollButton) {
                const currentHref = enrollButton.getAttribute('href');
                const separator = currentHref.includes('?') ? '&' : '?';
                const prefilledTitle = `[ENROLLMENT] ${titleParam} - `;
                enrollButton.setAttribute('href', currentHref + separator + `title=${encodeURIComponent(prefilledTitle)}`);
            }
        }
    }
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add active class to current navigation item
    const currentPath = window.location.pathname;
    document.querySelectorAll('.site-navigation a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
