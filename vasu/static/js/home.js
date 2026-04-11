window.onscroll = function () {
    let topBtn = document.getElementById("topBtn");
    if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
      topBtn.style.display = "block";
    } else {
      topBtn.style.display = "none";
    }
  };

  // Scroll to top smoothly
  function topFunction() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }