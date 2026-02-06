document.addEventListener("DOMContentLoaded", function () {
  const grid = document.querySelector(".video-grid");
  if (!grid) return;

  const albumId = grid.getAttribute("data-album-id") || "unknown";
  const storageKey = "album_scroll_" + albumId;

  const saved = sessionStorage.getItem(storageKey);
  if (saved !== null) {
    const y = parseInt(saved, 10);
    if (!isNaN(y)) {
      window.scrollTo(0, y);
    }
  }

  window.addEventListener("beforeunload", function () {
    sessionStorage.setItem(storageKey, String(window.scrollY));
  });

  grid.addEventListener("click", function (e) {
    const img = e.target.closest(".js-video-thumb");
    if (!img) return;

    const videoUrl = img.getAttribute("data-video-url");
    if (!videoUrl) return;

    const wrapper = img.closest(".video-thumb-wrapper");
    if (!wrapper) return;

    const video = document.createElement("video");
    video.setAttribute("controls", "controls");
    video.setAttribute("autoplay", "autoplay");
    video.src = videoUrl;

    wrapper.innerHTML = "";
    wrapper.appendChild(video);
  });
});
