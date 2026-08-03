/* ==========================================================================
   VISO - Lógica e Interactividad de la Web (JavaScript)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    /* ---------------------------------------------------------
       1. Sticky Header al hacer Scroll
       --------------------------------------------------------- */
    const header = document.querySelector('.header');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
            header.classList.add('sticky');
        } else {
            header.classList.remove('sticky');
        }
    });

    /* ---------------------------------------------------------
       2. Menú de Navegación Móvil (Toggle)
       --------------------------------------------------------- */
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            
            // Animación del botón hamburguesa
            const isActive = navMenu.classList.contains('active');
            mobileMenuBtn.style.transform = isActive ? 'rotate(90deg)' : 'rotate(0deg)';
        });

        // Cerrar menú al hacer clic en un enlace
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                mobileMenuBtn.style.transform = 'rotate(0deg)';
            });
        });
    }

    /* ---------------------------------------------------------
       3. Carrusel de Héroes (Hero Slideshow)
       --------------------------------------------------------- */
    const slides = document.querySelectorAll('.hero-slide');
    const prevBtn = document.querySelector('.carousel-control.prev');
    const nextBtn = document.querySelector('.carousel-control.next');
    const indicators = document.querySelectorAll('.carousel-indicators .indicator');
    
    let currentSlide = 0;
    const slideIntervalTime = 6000; // 6 segundos por slide
    let slideInterval;

    function showSlide(index) {
        // Asegurar rango circular
        if (index >= slides.length) {
            currentSlide = 0;
        } else if (index < 0) {
            currentSlide = slides.length - 1;
        } else {
            currentSlide = index;
        }

        // Cambiar clases en slides
        slides.forEach((slide, i) => {
            if (i === currentSlide) {
                slide.classList.add('active');
            } else {
                slide.classList.remove('active');
            }
        });

        // Cambiar clases en indicadores
        indicators.forEach((indicator, i) => {
            if (i === currentSlide) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    }

    function nextSlide() {
        showSlide(currentSlide + 1);
    }

    function prevSlide() {
        showSlide(currentSlide - 1);
    }

    function startAutoPlay() {
        stopAutoPlay(); // Prevenir múltiples timers
        slideInterval = setInterval(nextSlide, slideIntervalTime);
    }

    function stopAutoPlay() {
        if (slideInterval) {
            clearInterval(slideInterval);
        }
    }

    // Event Listeners de Controles Manuales
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            nextSlide();
            startAutoPlay(); // Reiniciar timer
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            prevSlide();
            startAutoPlay(); // Reiniciar timer
        });
    }

    indicators.forEach((indicator, i) => {
        indicator.addEventListener('click', () => {
            showSlide(i);
            startAutoPlay(); // Reiniciar timer
        });
    } );

    // Iniciar autoplay
    startAutoPlay();

    /* ---------------------------------------------------------
       4. Navegación por Pestañas en la Demo Interactiva
       --------------------------------------------------------- */
    const tabItems = document.querySelectorAll('.demo-nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');

            // Quitar clase activa de todas las pestañas
            tabItems.forEach(i => i.classList.remove('active'));
            // Ocultar todos los paneles de contenido
            tabPanes.forEach(p => p.classList.remove('active'));

            // Activar la pestaña clickeada
            item.classList.add('active');
            // Mostrar el panel correspondiente
            const activePane = document.getElementById(`pane-${targetTab}`);
            if (activePane) {
                activePane.classList.add('active');
            }
        });
    });

    /* ---------------------------------------------------------
       5. Simulador de Dashboard (Añadir Venta)
       --------------------------------------------------------- */
    const addSaleBtn = document.getElementById('add-sale-btn');
    let totalSalesToday = 1850.00;
    let salesCount = 4;
    let currentPercentage = 75;

    if (addSaleBtn) {
        addSaleBtn.addEventListener('click', () => {
            // Incrementar valores
            totalSalesToday += 250.00;
            salesCount += 1;
            
            // Incrementar meta diaria
            if (currentPercentage < 100) {
                currentPercentage += 10;
                if (currentPercentage > 100) currentPercentage = 100;
            }

            // Actualizar interfaz del simulador
            const salesValText = document.querySelector('#pane-dashboard .pane-grid-3 .pane-card:nth-child(1) .value');
            const salesSubText = document.querySelector('#pane-dashboard .pane-grid-3 .pane-card:nth-child(1) .sub');
            const progressPercentText = document.querySelector('.chart-box-header .percentage');
            const progressBar = document.querySelector('.progress-bar');

            if (salesValText) salesValText.textContent = `S/. ${totalSalesToday.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
            if (salesSubText) salesSubText.textContent = `${salesCount} Ventas Realizadas`;
            if (progressPercentText) progressPercentText.textContent = `${currentPercentage}% Completado`;
            if (progressBar) progressBar.style.width = `${currentPercentage}%`;

            // Efecto de feedback visual temporal en el botón
            addSaleBtn.textContent = 'Venta Registrada';
            addSaleBtn.style.background = 'var(--color-success)';
            setTimeout(() => {
                addSaleBtn.textContent = 'Añadir Venta Simulada (+ S/. 250)';
                addSaleBtn.style.background = 'var(--gradient-accent)';
            }, 1200);
        });
    }

    /* ---------------------------------------------------------
       6. Simulador de Citas (WhatsApp Alert)
       --------------------------------------------------------- */
    const whatsappBtns = document.querySelectorAll('.whatsapp-btn');
    const whatsappToast = document.getElementById('whatsapp-toast');

    whatsappBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.appointment-card-item');
            const name = card.querySelector('.app-info .name').textContent;
            const time = card.querySelector('.app-info .time').textContent;

            if (whatsappToast) {
                whatsappToast.textContent = `Mensaje enviado a ${name}: "Hola, le recordamos su cita el día de hoy a las ${time} en Óptica VISO. Le esperamos."`;
                whatsappToast.style.display = 'block';

                // Ocultar toast después de 4 segundos
                setTimeout(() => {
                    whatsappToast.style.display = 'none';
                }, 4000);
            }

            // Feedback en el botón presionado
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span>Mensaje Enviado</span>';
            btn.style.borderColor = 'var(--color-success)';
            btn.style.color = 'var(--color-success)';
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.style.borderColor = '';
                btn.style.color = '';
            }, 2500);
        });
    });

    /* ---------------------------------------------------------
       7. Simulador de Facturación (SUNAT e Impresora)
       --------------------------------------------------------- */
    const btnSunatSend = document.getElementById('btn-sunat-send');
    const btnTicketPrint = document.getElementById('btn-ticket-print');
    const sunatResponseMsg = document.getElementById('sunat-response-msg');

    if (btnSunatSend && sunatResponseMsg) {
        btnSunatSend.addEventListener('click', () => {
            sunatResponseMsg.textContent = 'Estado: Conectando con servidores de SUNAT...';
            sunatResponseMsg.style.borderLeftColor = 'var(--color-warning)';
            btnSunatSend.disabled = true;

            setTimeout(() => {
                sunatResponseMsg.innerHTML = '<strong>Estado: Aceptado.</strong> CDR Obtenida exitosamente (Código 0). Boleta B001-000084 enviada a SUNAT.';
                sunatResponseMsg.style.borderLeftColor = 'var(--color-success)';
                btnSunatSend.disabled = false;
            }, 1500);
        });
    }

    if (btnTicketPrint) {
        btnTicketPrint.addEventListener('click', () => {
            const originalText = btnTicketPrint.textContent;
            btnTicketPrint.textContent = 'Mandando a imprimir ticket...';
            btnTicketPrint.disabled = true;

            setTimeout(() => {
                btnTicketPrint.textContent = 'Ticket Impreso';
                btnTicketPrint.style.background = 'rgba(16, 185, 129, 0.1)';
                btnTicketPrint.style.color = 'var(--color-success)';
                btnTicketPrint.style.borderColor = 'var(--color-success)';
            }, 1000);

            setTimeout(() => {
                btnTicketPrint.textContent = originalText;
                btnTicketPrint.style.background = '';
                btnTicketPrint.style.color = '';
                btnTicketPrint.style.borderColor = '';
                btnTicketPrint.disabled = false;
            }, 3000);
        });
    }

    /* ---------------------------------------------------------
       8. Manejo del Formulario de Contacto
       --------------------------------------------------------- */
    const contactForm = document.getElementById('contact-form');
    const formSuccess = document.getElementById('form-success');

    if (contactForm && formSuccess) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();

            const submitBtn = contactForm.querySelector('button[type="submit"]');

            // Cambiar a estado cargando
            submitBtn.textContent = 'Enviando solicitud...';
            submitBtn.disabled = true;

            // Simular respuesta del servidor
            setTimeout(() => {
                submitBtn.style.display = 'none';
                formSuccess.style.display = 'block';
                contactForm.reset();
            }, 1200);
        });
    }
});
