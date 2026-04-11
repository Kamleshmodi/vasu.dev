document.addEventListener("DOMContentLoaded", function () {
    const mainImage = document.getElementById("mainImage");
    const thumbnails = document.querySelectorAll(".thumbnails img");

    thumbnails.forEach(function (thumbnail) {
        thumbnail.addEventListener("click", function () {
            mainImage.src = this.src;
        });
    });
});
