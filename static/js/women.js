function toggleWishlist(el) {
    el.classList.toggle("active");
    const icon = el.querySelector("i");
    if (el.classList.contains("active")) {
        icon.classList.remove("far");
        icon.classList.add("fas");
    } else {
        icon.classList.remove("fas");
        icon.classList.add("far");
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const mobileFilterToggle = document.querySelector('.mobile-filter-toggle');
    const leftSidebar = document.querySelector('.left-sidebar');

    if (mobileFilterToggle && leftSidebar) {
        mobileFilterToggle.addEventListener('click', () => {
            leftSidebar.classList.toggle('open');
            const isExpanded = leftSidebar.classList.contains('open');
            mobileFilterToggle.setAttribute('aria-expanded', String(isExpanded));
        });
    }

    // Handling the collapsible category and other filters
    const filterBlocks = document.querySelectorAll(".filter-block");
    
    filterBlocks.forEach(block => {
        const title = block.querySelector(".filter-title");
        const options = block.querySelector("ul");
        const icon = title.querySelector(".toggle-icon");
        if (!title || !options || !icon) {
            return;
        }
        
        // This is the new logic: all filter blocks are open by default.
        // We only need to check if they have an active item.
        const hasActiveItem = options.querySelector(".active-category");
        options.classList.remove("hidden"); // Remove the 'hidden' class to keep it open
        icon.textContent = "-"; // Set the icon to '-' to show it's open
        
        // Add event listener for toggling on click
        title.addEventListener("click", function() {
            if (options.classList.contains("hidden")) {
                options.classList.remove("hidden");
                icon.textContent = "-";
            } else {
                options.classList.add("hidden");
                icon.textContent = "+";
            }
        });
    });

    // Handling the dropdowns (Designer, Size, Color)
    const dropdowns = document.querySelectorAll('.dropdown');

    dropdowns.forEach(dropdown => {
        const dropbtn = dropdown.querySelector('.dropbtn');
        const dropdownContent = dropdown.querySelector('.dropdown-content');
        if (!dropbtn || !dropdownContent) {
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