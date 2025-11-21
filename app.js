window.onload = () => {
    // Arkaplan fade
    document.querySelector(".bg").style.opacity = "1";

    // Tapınak aşağıdan yukarı
    const temple = document.querySelector(".temple");
    temple.style.bottom = "40px";
    temple.style.opacity = "1";

    // Hero text
    setTimeout(() => {
        const text = document.querySelector(".hero-text");
        text.style.opacity = "1";
        text.style.transform = "translateY(0)";
    }, 900);

    // CTA buton
    setTimeout(() => {
        const button = document.querySelector(".cta-button");
        button.style.opacity = "1";
        button.style.transform = "translateY(0)";
    }, 1200);
};
