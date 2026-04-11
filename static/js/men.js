document.addEventListener('DOMContentLoaded', () => {
    const mobileFilterToggle = document.querySelector('.mobile-filter-toggle');
    const leftSidebar = document.querySelector('.left-sidebar');

    if (mobileFilterToggle && leftSidebar) {
        mobileFilterToggle.addEventListener('click', () => {
            leftSidebar.classList.toggle('open');
            const isExpanded = leftSidebar.classList.contains('open');
            mobileFilterToggle.setAttribute('aria-expanded', String(isExpanded));
        });
    }

    const filterTitles = document.querySelectorAll('.filter-title');
    filterTitles.forEach(title => {
        title.addEventListener('click', () => {
            const filterOptions = title.nextElementSibling;
            if (filterOptions) {
                filterOptions.classList.toggle('hidden');
                const toggleIcon = title.querySelector('.toggle-icon');
                if (filterOptions.classList.contains('hidden')) {
                    toggleIcon.textContent = '+';
                } else {
                    toggleIcon.textContent = '-';
                }
            }
        });
    });

    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const dropbtn = dropdown.querySelector('.dropbtn');
        if (!dropbtn) {
            return;
        }

        dropbtn.addEventListener('click', (event) => {
            event.preventDefault();
            dropdown.classList.toggle('open');
        });
    });

    document.addEventListener('click', (event) => {
        dropdowns.forEach((dropdown) => {
            if (!dropdown.contains(event.target)) {
                dropdown.classList.remove('open');
            }
        });
    });
});